"""Weekly summary email module for FabOMatic."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from threading import Thread

from sqlalchemy.orm import Session
from flask import render_template, g
from flask_mail import Mail, Message
from flask_babel import force_locale

from FabOMatic.database.models import User, Machine, Use, UnknownCard
from FabOMatic.database.repositories import UserRepository, MachineRepository
from FabOMatic.conf import FabConfig


class WeeklySummaryData:
    """Data class for weekly summary information."""

    def __init__(self):
        self.machine_stats: List[Dict] = []
        self.pending_maintenances: List[Dict] = []
        self.unrecognized_cards: List[Dict] = []
        self.week_start: datetime = None
        self.week_end: datetime = None


class WeeklySummaryRepository:
    """Repository for weekly summary queries."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_week_bounds(self) -> Tuple[datetime, datetime]:
        """Get the start and end timestamps for the previous week (Sunday to Sunday).

        Returns:
            Tuple[datetime, datetime]: Start and end datetime objects for the week.
        """
        now = datetime.now()
        # Calculate last Sunday (end of week)
        days_since_sunday = (now.weekday() + 1) % 7
        last_sunday = now - timedelta(days=days_since_sunday)
        week_end = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Calculate Sunday a week before (start of week)
        week_start = (last_sunday - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

        return week_start, week_end

    def get_weekly_machine_stats(self, week_start: datetime, week_end: datetime) -> List[Dict]:
        """Get machine usage statistics for the week.

        Args:
            week_start: Start of the week
            week_end: End of the week

        Returns:
            List of dictionaries with machine statistics
        """
        start_timestamp = week_start.timestamp()
        end_timestamp = week_end.timestamp()

        # Query all uses in the time range
        uses = (
            self.db_session.query(Use)
            .filter(
                Use.start_timestamp >= start_timestamp,
                Use.start_timestamp <= end_timestamp,
                Use.end_timestamp.is_not(None),
            )
            .all()
        )

        # Aggregate by machine
        machine_times: Dict[int, float] = {}
        for use in uses:
            machine_id = use.machine_id
            duration = use.end_timestamp - use.start_timestamp
            machine_times[machine_id] = machine_times.get(machine_id, 0) + duration

        # Build result with machine details
        result = []
        for machine_id, total_seconds in machine_times.items():
            machine = self.db_session.query(Machine).filter_by(machine_id=machine_id).first()
            if machine:
                result.append(
                    {
                        "machine_id": machine_id,
                        "machine_name": machine.machine_name,
                        "total_hours": total_seconds / 3600.0,
                        "total_seconds": total_seconds,
                    }
                )

        # Sort by usage time (descending)
        result.sort(key=lambda x: x["total_hours"], reverse=True)
        return result

    def get_pending_maintenances(self) -> List[Dict]:
        """Get all machines with pending maintenance.

        Returns:
            List of dictionaries with pending maintenance information
        """
        result = []
        machine_repo = MachineRepository(self.db_session)
        machines = machine_repo.get_all()

        for machine in machines:
            for maintenance in machine.maintenances:
                relative_time = machine_repo.getRelativeUseTimeByMaintenance(machine.machine_id, maintenance)
                required_time = maintenance.hours_between * 3600.0

                if relative_time > required_time:
                    # Calculate how overdue it is
                    overdue_hours = (relative_time - required_time) / 3600.0

                    result.append(
                        {
                            "machine_id": machine.machine_id,
                            "machine_name": machine.machine_name,
                            "maintenance_description": maintenance.description,
                            "overdue_hours": overdue_hours,
                            "instructions_url": maintenance.instructions_url or "",
                        }
                    )

        # Sort by most overdue first
        result.sort(key=lambda x: x["overdue_hours"], reverse=True)
        return result

    def get_unrecognized_cards(self, week_start: datetime, week_end: datetime) -> List[Dict]:
        """Get all unrecognized cards scanned during the week.

        Args:
            week_start: Start of the week
            week_end: End of the week

        Returns:
            List of dictionaries with unrecognized card information
        """
        start_timestamp = week_start.timestamp()
        end_timestamp = week_end.timestamp()

        cards = (
            self.db_session.query(UnknownCard)
            .filter(UnknownCard.timestamp >= start_timestamp, UnknownCard.timestamp <= end_timestamp)
            .all()
        )

        # Deduplicate by card_UUID and collect machine names
        card_dict: Dict[str, Dict] = {}
        for card in cards:
            uuid = card.card_UUID
            machine = self.db_session.query(Machine).filter_by(machine_id=card.machine_id).first()
            machine_name = machine.machine_name if machine else f"Machine {card.machine_id}"

            if uuid not in card_dict:
                card_dict[uuid] = {
                    "card_uuid": uuid,
                    "machines": set(),
                    "first_seen": card.timestamp,
                    "count": 0,
                }

            card_dict[uuid]["machines"].add(machine_name)
            card_dict[uuid]["count"] += 1
            card_dict[uuid]["first_seen"] = min(card_dict[uuid]["first_seen"], card.timestamp)

        # Convert to list and format
        result = []
        for uuid, data in card_dict.items():
            result.append(
                {
                    "card_uuid": uuid,
                    "machines": sorted(list(data["machines"])),
                    "first_seen": datetime.fromtimestamp(data["first_seen"]),
                    "attempt_count": data["count"],
                }
            )

        # Sort by first seen
        result.sort(key=lambda x: x["first_seen"])
        return result


class WeeklySummaryMailer:
    """Handles sending weekly summary emails."""

    def __init__(self, db_session: Session, mail: Mail, app):
        self.db_session = db_session
        self.mail = mail
        self.app = app

    def send_async_email(self, app, msg):
        """Send email in background thread with app context."""
        with app.app_context():
            try:
                logging.info("Attempting to send weekly summary email to: %s", msg.recipients)
                self.mail.send(msg)
                logging.info("Weekly summary email sent successfully to: %s", msg.recipients)
            except Exception as e:
                logging.error("Failed to send weekly summary email: %s (type: %s)", str(e), type(e).__name__)

    def send_weekly_summary(self, user: User, summary_data: WeeklySummaryData, language: str = "en") -> bool:
        """Send weekly summary email to a user.

        Args:
            user: User to send email to
            summary_data: Weekly summary data
            language: Language for the email (en or it)

        Returns:
            True if email was queued successfully, False otherwise
        """
        if not user.email:
            logging.warning(f"User {user.user_id} ({user.name} {user.surname}) has no email address")
            return False

        try:
            try:
                base_url = FabConfig.getSetting("web", "base_url")
            except (KeyError, TypeError):
                base_url = "localhost:23336"

            # Use force_locale to set the language context for Babel
            with force_locale(language):
                # Determine subject based on language
                if language == "it":
                    subject = "FabOMatic - Riepilogo Settimanale"
                else:
                    subject = "FabOMatic - Weekly Summary"

                msg = Message(subject, recipients=[user.email])

                # Set language in g for template access
                g.language = language

                # Render both HTML and plain text versions
                template_name = "weekly_summary_email"
                msg.html = render_template(
                    f"{template_name}.html",
                    user=user,
                    summary_data=summary_data,
                    base_url=base_url,
                )
                msg.body = render_template(
                    f"{template_name}.txt",
                    user=user,
                    summary_data=summary_data,
                    base_url=base_url,
                )

            # Send email in background thread
            Thread(target=self.send_async_email, args=(self.app, msg)).start()
            logging.info(f"Weekly summary email queued for {user.email}")
            return True

        except Exception as e:
            logging.error(f"Failed to queue weekly summary email for {user.email}: {str(e)}")
            return False


def send_weekly_summaries(db_session: Session, mail: Mail, app) -> Dict[str, int]:
    """Send weekly summaries to all users with email addresses.

    Args:
        db_session: Database session
        mail: Flask-Mail instance
        app: Flask app instance

    Returns:
        Dictionary with statistics (sent, failed, skipped)
    """
    # Check if weekly summaries are enabled
    try:
        enabled = FabConfig.getSetting("weekly_summary", "enabled")
    except (KeyError, TypeError):
        enabled = True  # Default to enabled if not configured

    if not enabled:
        logging.info("Weekly summaries are disabled in configuration")
        return {"sent": 0, "failed": 0, "skipped": 0}

    try:
        language = FabConfig.getSetting("weekly_summary", "language")
    except (KeyError, TypeError):
        language = "en"  # Default to English if not configured

    logging.info(f"Generating weekly summaries in language: {language}")

    # Gather data
    repo = WeeklySummaryRepository(db_session)
    summary_data = WeeklySummaryData()
    summary_data.week_start, summary_data.week_end = repo.get_week_bounds()
    summary_data.machine_stats = repo.get_weekly_machine_stats(summary_data.week_start, summary_data.week_end)
    summary_data.pending_maintenances = repo.get_pending_maintenances()
    summary_data.unrecognized_cards = repo.get_unrecognized_cards(summary_data.week_start, summary_data.week_end)

    logging.info(
        f"Weekly summary data: {len(summary_data.machine_stats)} machines, "
        f"{len(summary_data.pending_maintenances)} pending maintenances, "
        f"{len(summary_data.unrecognized_cards)} unrecognized cards"
    )

    # Send to all users with email addresses
    user_repo = UserRepository(db_session)
    users = user_repo.get_all()

    mailer = WeeklySummaryMailer(db_session, mail, app)

    stats = {"sent": 0, "failed": 0, "skipped": 0}

    for user in users:
        if user.disabled or user.deleted:
            stats["skipped"] += 1
            continue

        if not user.email:
            stats["skipped"] += 1
            continue

        # Check if user wants to receive weekly summaries
        if not user.receive_weekly_summary:
            stats["skipped"] += 1
            continue

        if mailer.send_weekly_summary(user, summary_data, language):
            stats["sent"] += 1
        else:
            stats["failed"] += 1

    logging.info(f"Weekly summary sending completed: {stats}")
    return stats
