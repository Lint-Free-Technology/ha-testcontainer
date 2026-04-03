# ha-config/www/

This directory is served by Home Assistant at the `/local/` URL path.

Frontend plugins (Lovelace dashboard cards and modules) are downloaded here
by `scripts/fetch_plugin.py` and served at:

    /local/dashboard/<plugin-name>/<file>.js

## Usage

```bash
# Download a plugin and register it as a Lovelace resource:
python scripts/fetch_plugin.py custom-cards/button-card
python scripts/fetch_plugin.py thomasloven/lovelace-card-mod 3.4.4
python scripts/fetch_plugin.py custom-cards/button-card --list   # list releases

# Or via make:
make fetch-plugin PLUGIN=custom-cards/button-card
make fetch-plugin PLUGIN=thomasloven/lovelace-card-mod VERSION=3.4.4
```

The script places JS files in `www/dashboard/<plugin-name>/` and registers the
resource URL in `ha-config/lovelace_resources.yaml`, which is included by
`configuration.yaml` under `lovelace.resources`.

## What's committed

Only this README is committed.  All downloaded plugin JS files are excluded
by `.gitignore` so the repository stays lightweight.  The `lovelace_resources.yaml`
file **is** committed so the resource list is part of the test configuration.
