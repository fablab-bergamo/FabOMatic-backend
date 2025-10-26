# Fab-O-Matic back-end

[![Build, test and package](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/build.yml/badge.svg)](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/build.yml)

**[English](README.md)** | **Italiano**

## Cos'è questo progetto?

* Questa è un'applicazione web per gestire l'accesso alle macchine del FabLab tramite schede Fab-O-Matic collegate alle macchine (vedi progetto ESP32: [Fab-O-Matic](https://github.com/fablab-bergamo/Fab-O-matic))

* Esempio di schermata principale, con stato delle macchine in tempo reale:

![Dashboard Macchine](doc/media/about.png)

* **Manuale Utente**: [Versione PDF](doc/UI.pdf) | [Versione Markdown](doc/UI.it.md)

* Questa applicazione Python 3.10 esegue un client MQTT e un'applicazione Flask HTTPS.

* Articoli che descrivono il progetto sono disponibili sul sito del FabLab Bergamo: <https://www.fablabbergamo.it/2024/07/14/fabomatic7/>

## Funzionalità

* Portale web di amministrazione con autenticazione utente su HTTPS

* Gestisce il database delle tessere RFID dei membri con il loro stato (attivo, inattivo). Facile registrazione di nuovi membri (passa la tessera su un Fab-O-Matic esistente e converti in nuovo utente).

* Piani di manutenzione delle macchine basati sulle ore effettive con visualizzazione sul display LCD del Fab-O-Matic

* Permessi per utente e macchina (possono essere disabilitati)

* Cronologia delle macchine (uso e manutenzione)

* Dashboard in tempo reale dello stato delle macchine

## Requisiti runtime del backend

* Un Broker MQTT esterno. Mosquitto è stato utilizzato per i test.

* SQLAlchemy supporta diversi motori di database, ma questo è stato testato solo con SQLite.

## Pre-requisiti per Raspberry Pi Zero

* Installare i prerequisiti (python 3.10+, rustc per la crittografia, mosquitto, pip). Il completamento dell'installazione richiede 3-4 ore su Raspberry Pi Zero.

```shell
wget -qO - https://raw.githubusercontent.com/tvdsluijs/sh-python-installer/main/python.sh | sudo bash -s 3.10.9
sudo apt remove python3-apt
sudo apt install python3-apt
sudo curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
sudo apt install mosquitto
```

## Pre-requisiti per macchine Linux

* Su altri sistemi Linux, i seguenti requisiti dovrebbero essere sufficienti:

```shell
sudo apt install python3-apt
sudo apt install rustc
sudo apt install mosquitto
sudo apt install dbus-user-session
```

## Pre-requisiti per aggiornamenti firmware

* Lo strumento ESPOTA di Espressif viene utilizzato per applicare aggiornamenti firmware Over-the-air alle schede Fab-O-Matic.

```shell
wget https://raw.githubusercontent.com/espressif/arduino-esp32/master/tools/espota.py
```

## Istruzioni per l'installazione

* Installare dal repository PyPI

```shell
pip install FabOMatic
```

* Nella directory di installazione del pacchetto, copiare src/FabOMatic/conf/settings.example.toml in settings.toml e modificare le impostazioni.
  Alla prima esecuzione, se il file settings.toml è mancante, il file settings.example.toml verrà copiato e utilizzato al suo posto.

* Testare con

```shell
python -m FabOMatic 5
```

* Dopo l'installazione accedere con l'email admin predefinita nel file delle impostazioni e la password "admin".

> L'URL predefinito è https://HOSTNAME:23336/

* Impostare una strategia di backup per il database (database.sqldb), che viene creato automaticamente alla prima esecuzione.

* Configurare systemd per avviare automaticamente il modulo Python all'avvio con il profilo utente:

Vedere l'esempio di configurazione in doc/systemd

## Come aggiornare la versione

* Usare pip --upgrade:

```shell
pip install FabOMatic --upgrade
```

* Rivedere il file settings.toml dopo l'installazione.

* Gli aggiornamenti del database vengono applicati da Alembic all'avvio del backend e non dovrebbero richiedere interazione dell'utente.

## File di configurazione

* Per la configurazione, viene utilizzato il file src/FabOMatic/conf/settings.toml nella directory di installazione del pacchetto.
* Contiene informazioni di configurazione per il server MQTT (obbligatorio), stringa di connessione al database (obbligatorio), SMTP per l'email "password dimenticata" (non obbligatorio) e impostazioni del riepilogo settimanale (opzionale)
* Esempio qui sotto

```text
[database]
url = "sqlite:///machines.sqldb"
name = "fablab"

[MQTT]
broker = "127.0.0.1"
port = 1883
client_id = "backend"
topic = "machine/"        # topic principale. I sottotopic /machine/<ID> saranno sottoscritti
reply_subtopic = "/reply"  # aggiunto ai topic delle macchine per le risposte dal backend. Es. machine/1/reply
stats_topic = "stats/"

[web]
secret_key = "some_long_hex_string_1234gs"  # Usato per la crittografia
default_admin_email = "admin@fablag.org"    # Usato per il login iniziale
base_url = "fabpi.example.com"              # URL base per l'applicazione web (usato nelle email)

[email]
server = "smtp.google.com"
port = 587
use_tls = true
username = ""
password = ""
sender = "admin@fablab.org"

[weekly_summary]
enabled = true    # Abilita email di riepilogo settimanale
language = "it"   # Lingua per le email: "en" o "it"

```

## Note per gli sviluppatori

* Sviluppato con VSCode, estensioni: Python, SQLTools, SQLTools SQLite, Black formatter

* Creare un venv python con Python >=3.10 e assicurarsi che il terminale abbia attivato il venv

* Le impostazioni di test sono nel file tests\test_settings.toml, per eseguire i test dalla cartella root (o Terminal)

```shell
pytest -v
```

* Come eseguire il server da Terminal (dalla cartella root)

```shell
pip install -e .
python ./run.py
```

* Requisiti del pacchetto / Come creare il pacchetto (vedi [Documentazione Python](https://packaging.python.org/en/latest/tutorials/packaging-projects/))

```shell
pip install --upgrade build
pip install --upgrade twine
```

Per aggiornare la distribuzione

```shell
python -m build
python -m twine upload dist/*
```

* Per gestire le modifiche allo schema con installazioni esistenti, modificare database/models.py, verificare che le modifiche siano correttamente catturate da alembic, quindi generare uno script di migrazione e applicarlo. Quindi committare tutti i file e pubblicare una nuova revisione.

```shell
alembic check
alembic revision --autogenerate -m "Descrizione della modifica"
alembic upgrade head
```

* Per gestire la migrazione dei dati è necessario modificare manualmente il file di migrazione generato nella cartella alembic.

* Dopo aver testato il nuovo schema del database, archiviare una copia di simple-db.sqldb (generato da pytest) nella cartella tests/databases con il nome della revisione. Questo garantirà che le migrazioni vengano testate su questa nuova versione in futuro.

* Traduzioni con Babel

Estrazione iniziale (eseguire dalla cartella src/FabOMatic)

```shell
pybabel extract -F babel.cfg -o messages.pot ./
```

Aggiornamento unendo le modifiche nei file di traduzione

```shell
pybabel update -i messages.pot -d translations
```

Aggiunta di una nuova lingua

```shell
pybabel init -i messages.pot -d translations -l <locale>
```

Compilazione delle modifiche

```shell
pybabel compile -d translations
```

## Conformità GDPR ⚖️

Le tessere RFID dei membri saranno collegate a una persona fisica e pertanto, *è necessario* raccogliere il consenso scritto di questa persona come parte dell'accordo di adesione.

### Accordo GDPR suggerito

* Il motivo della raccolta dei dati è *controllare l'utilizzo delle attrezzature del FabLab per una migliore manutenzione delle attrezzature e la sicurezza fisica degli utenti del FabLab*.
* Il periodo di conservazione dei dati per i dati anagrafici RFID è per la durata dell'adesione al FabLab con un minimo di *un anno*.
* Il periodo di conservazione dei dati dei record storici, inclusi nome utente, ora di utilizzo, macchina utilizzata, operazione di manutenzione eseguita è *un anno*.
* Dopo 1 anno, i dati nominativi storici vengono automaticamente sostituiti con dati utente anonimi.
* Il sistema può raccogliere ID di tag RFID da tessere vicine, non collegate ai dati anagrafici RFID del FabLab. Tali informazioni verranno eliminate dopo *un mese*.
* Le persone responsabili del trattamento dei dati sono gli utenti amministrativi di Fab-O-Matic.
* Le informazioni raccolte non vengono condivise al di fuori del sistema Fab-O-Matic o divulgate al di fuori degli amministratori di Fab-O-Matic.

### Cosa è necessario fare

* È *necessario* proteggere l'accesso al webserver backend di Fab-O-Matic e agli host fisici (utilizzare una politica password appropriata).
* È *necessario* programmare un lavoro cron giornaliero per garantire che i dati vengano eliminati dal database e dai file di log

```shell
python -m FabOMatic --purge
journalctl --vacuum-time=1y
```

* Per garantire le richieste di accesso ai dati, è possibile utilizzare la funzione di esportazione Excel filtrando i dati per utente.
* Per garantire il diritto alla cancellazione, è possibile utilizzare i pulsanti Elimina nelle pagine Uso, Interventi e Utente.

## Email di Riepilogo Settimanale 📧

Fab-O-Matic può inviare email di riepilogo settimanale automatiche agli utenti con statistiche sull'utilizzo delle macchine, manutenzioni in sospeso e tessere non riconosciute.

### Configurazione

Aggiungere le seguenti impostazioni al file `settings.toml`:

```toml
[web]
base_url = "your.external.url.for.fabomatic"  # Il tuo URL di FabOMatic (usato nei link delle email)

[weekly_summary]
enabled = true       # Abilita/disabilita email di riepilogo settimanale
language = "it"      # Lingua per le email: "en" o "it"
```

### Configurazione Utente

* Gli utenti devono avere un indirizzo email configurato nel loro profilo
* Gli utenti devono abilitare la casella "Ricevi email di riepilogo settimanale" nel loro profilo
* Questo può essere configurato quando si aggiungono o modificano utenti nell'interfaccia di amministrazione

### Pianificazione dei Riepiloghi Settimanali

Configurare un lavoro cron per inviare i riepiloghi settimanali. Ad esempio, per inviare ogni domenica alle 9:00:

```shell
# Modificare crontab
crontab -e

# Aggiungere questa riga per inviare riepiloghi settimanali ogni domenica alle 9:00
0 9 * * 0 cd /path/to/FabOMatic && /path/to/venv/bin/python -m FabOMatic --weekly-summary --loglevel 40
```

### Contenuto delle Email

Le email di riepilogo settimanale includono:
* **Statistiche di Utilizzo delle Macchine**: Tempo trascorso su ogni macchina durante la settimana (da domenica a domenica)
* **Manutenzioni in Sospeso**: Elenco delle macchine che richiedono manutenzione con ore di ritardo
* **Tessere Non Riconosciute**: Tessere RFID che hanno tentato l'accesso ma non sono registrate
* **Link diretto**: Link all'interfaccia web di FabOMatic per maggiori dettagli

### Test

Per attivare manualmente un'email di riepilogo settimanale:

```shell
python -m FabOMatic --weekly-summary
```

## Registro delle revisioni principali

| Versione | Quando | Note di rilascio |
|--|--|--|
| 0.0.18 | Gennaio 2024 | Prima revisione con Alembic per il tracciamento della versione del database per gestire aggiornamenti graduali |
| 0.1.15 | Febbraio 2024 | Interfaccia migliorata su mobile, corretti usi duplicati, aggiunta definizione del periodo di grazia sui tipi di macchina, aggiunta pagina di sistema |
| 0.2.0 | Febbraio 2024 | Traduzioni UI con flask-babel (IT, EN), aggiunti dettagli schede nella pagina di sistema |
| 0.3.0 | Maggio 2024 | Le autorizzazioni utente possono essere disabilitate per tipo di macchina, aggiunto campo URL manutenzione, miglioramenti pagina Sistema (ricarica DB, file di log) |
| 0.4.0 | Giugno 2024 | Messaggi bufferizzati inviati dalle schede Fab-O-Matic sono contrassegnati con un'icona dell'orologio. |
| 0.5.0 | Giugno 2024 | Primo rilascio su PyPI. Rinominato in FabOMatic. Aggiunta conformità GDPR (funzione di eliminazione) |
| 0.6.0 | Agosto 2024 | Aggiunti comandi remoti dal backend per stampanti abilitate al cloud come BambuLab |
| 0.7.0 | Dicembre 2024 | Rilascio di correzione bug, nessuna nuova funzionalità |
| 0.7.4 | Ottobre 2024 | Aggiunta nuova pagina impostazioni in Sistemi, risolto problema di blocco email |
| 1.0.0 | Ottobre 2025 | **Rilascio maggiore**: Modernizzazione completa dell'interfaccia utente con design moderno, funzionalità di ricerca/filtro, navigazione migliorata, design responsive ed esperienza utente migliorata |
| 1.0.1 | Ottobre 2025 | Aggiunta funzionalità email di riepilogo settimanale con report automatici delle attività, avvisi di manutenzione in sospeso e tracciamento tessere non riconosciute. Risolto bug di rendering dei link HTML nelle email. |
