# Configuration

The current inventory-only stage has no persistent configuration and does not
read environment variables. It makes no API requests and does not store
credentials. Run the `inventory` command to collect local data.

Backend URL, heartbeat interval, protected configuration storage, and device
credentials are intentionally deferred until API contracts and enrollment
security are coordinated with the CUT-CLMS API project.
