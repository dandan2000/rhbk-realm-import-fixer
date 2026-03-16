# rhbk-realm-import-fixer

Script para solucionar problema

"could not create realm Protocol mapper name must be unique per protocol" al importar un Realm en RHBK 26.4 desde un json exportado en un version SSO 7.6

python3 fix_keycloak_mappers.py /path/to/dev-realm-realm.json -o realm_listo_para_importar.json
