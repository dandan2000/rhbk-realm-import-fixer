import json
import argparse
import sys
import os

def fix_protocol_mappers(entities, entity_type):
    fixes_made = 0
    for entity in entities:
        if 'protocolMappers' in entity:
            seen_keys = set()
            
            for mapper in entity['protocolMappers']:
                protocol = mapper.get('protocol')
                name = mapper.get('name')
                
                if protocol and name:
                    key = (protocol, name)
                    original_name = name
                    counter = 1
                    
                    while key in seen_keys:
                        new_name = f"{original_name}_dup{counter}"
                        mapper['name'] = new_name
                        key = (protocol, new_name)
                        counter += 1
                        fixes_made += 1
                        
                        entity_id = entity.get('clientId', entity.get('name', 'desconocido'))
                        print(f"[-] Corregido en {entity_type} '{entity_id}': ")
                        print(f"    Renombrado mapper '{original_name}' -> '{new_name}' (Protocolo: {protocol})")
                    
                    seen_keys.add(key)
                    
    return fixes_made

def process_realm(input_file, output_file):
    print(f"Analizando el archivo: {input_file}...\n")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            realm_data = json.load(f)
    except FileNotFoundError:
        print(f"[!] Error: No se encontró el archivo '{input_file}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"[!] Error: El archivo '{input_file}' no es un JSON válido.")
        sys.exit(1)

    total_fixes = 0

    if 'clients' in realm_data:
        total_fixes += fix_protocol_mappers(realm_data['clients'], "Cliente")
    
    if 'clientScopes' in realm_data:
        total_fixes += fix_protocol_mappers(realm_data['clientScopes'], "Client Scope")

    if total_fixes > 0:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(realm_data, f, indent=2)
            print(f"\n[+] ¡Éxito! Se corrigieron {total_fixes} mappers duplicados.")
            print(f"[+] El Realm corregido se guardó en: {output_file}")
        except Exception as e:
            print(f"[!] Error al escribir el archivo {output_file}: {e}")
    else:
        print("[!] No se encontraron mappers duplicados. El archivo está correcto respecto a este problema.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Corrige el error de mappers duplicados en exportaciones de Keycloak.")
    parser.add_argument("input", help="Ruta al archivo JSON original del Realm de Keycloak")
    parser.add_argument("-o", "--output", help="Ruta para el archivo JSON de salida (Opcional)")
    
    args = parser.parse_args()
    
    # Lógica para determinar el nombre de salida dinámico
    if args.output:
        final_output = args.output
    else:
        # Separa el nombre base de la extensión (ej: "archivo", ".json")
        base_name, extension = os.path.splitext(args.input)
        final_output = f"{base_name}-FIXED{extension}"
        
    process_realm(args.input, final_output)