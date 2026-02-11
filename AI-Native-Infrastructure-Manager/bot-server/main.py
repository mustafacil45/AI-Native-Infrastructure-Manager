
from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

import argparse
import jsonschema

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--listen', default='0.0.0.0:5003')
args = parser.parse_args()

# Configuration
SCHEMA_SERVICE_URL = os.environ.get('SCHEMA_SERVICE_URL', 'http://localhost:5001')
VALUES_SERVICE_URL = os.environ.get('VALUES_SERVICE_URL', 'http://localhost:5002')
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://host.docker.internal:11434')
MODEL_NAME = os.environ.get('MODEL_NAME', 'llama3')

import sys

def query_ollama(prompt):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    try:
        print(f"Querying Ollama with prompt length: {len(prompt)}", flush=True)
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
        response.raise_for_status()
        res_json = response.json()
        return res_json.get('response', '').strip(), None
    except Exception as e:
        print(f"Error querying Ollama: {e}", flush=True)
        return None, str(e)

def get_app_name_safe(user_input, ai_response):
    valid_apps = ["tournament", "matchmaking", "chat"]
    if not ai_response:
        ai_response = ""
    clean_ai_res = ai_response.strip().lower().replace(".", "") # Temizlik
    
    # 1. AI doğru bildiyse onu kullan
    if clean_ai_res in valid_apps:
        return clean_ai_res
        
    # 2. AI şaşırdıysa mesajın içinde kelime ara (Fallback)
    for app in valid_apps:
        if app in user_input.lower():
            return app
            
    return None

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"success": True, "status": "healthy"}), 200

@app.route('/ready', methods=['GET'])
def ready_check():
    return jsonify({"success": True, "status": "ready"}), 200

@app.route('/message', methods=['POST'])
def handle_message():
    data = request.json
    user_input = data.get('input') or data.get('text')
    
    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    # Step 1: Identify application
    IDENTIFY_PROMPT = f"""
    Sana bir kullanıcı mesajı vereceğim. Bu mesajın aşağıdaki listedeki uygulamalardan hangisiyle ilgili olduğunu bulman gerekiyor.
    
    YASAL LİSTE: ['tournament', 'matchmaking', 'chat']

    Kullanıcı Mesajı: "{user_input}"

    KURALLAR:
    1. Cevap SADECE listedeki kelimelerden biri olabilir: 'tournament', 'matchmaking', 'chat'.
    2. Eğer kullanıcı mesajında bu kelimelerden biri GEÇMİYORSA veya "unicorn", "payment" gibi listede olmayan bir uygulama isteniyorsa, ASLA tahmin yapma.
    3. Bilinmeyen veya listede olmayan her türlü uygulama için 'none' cevabını ver.
    4. Sadece tek bir kelime cevap ver. Başka hiçbir şey yazma.
    
    Örnekler:
    - "set tournament memory" -> tournament
    - "update unicorn service" -> none
    - "change memory of payment app" -> none
    - "set chat cpu" -> chat

    Cevap:"""
    
    ai_response, err = query_ollama(IDENTIFY_PROMPT)
    if err:
        return jsonify({"error": f"AI identification failed: {err}"}), 500

    app_name = get_app_name_safe(user_input, ai_response)

    # Strict check: If AI said 'none' explicitly, fail immediately.
    if ai_response.strip().lower() == 'none':
        return jsonify({"error": "Application not found in allowed list (tournament, matchmaking, chat)."}), 404

    if not app_name:
        return jsonify({"error": f"Could not identify application. AI said: '{ai_response}'"}), 400
    
    # Step 2: Fetch Schema and Values
    try:
        # Schema Service
        schema_resp = requests.get(f"{SCHEMA_SERVICE_URL}/{app_name}")
        schema_resp.raise_for_status()
        schema = schema_resp.json()

        # Values Service - Updated Endpoint Path (No /values prefix anymore)
        values_resp = requests.get(f"{VALUES_SERVICE_URL}/{app_name}")
        values_resp.raise_for_status()
        values = values_resp.json()
        current_values = json.dumps(values, indent=2) 
        
    except Exception as e:
        return jsonify({"error": f"Could not fetch data: {str(e)}"}), 500

    # Step 3: Generate update instructions (Patching Strategy)
    UPDATE_PROMPT = f"""
    Sen uzman bir DevOps mühendisisin ve katı bir JSON Schema doğrulayıcısısın.
    
    GÖREV: Kullanıcının isteğine göre, verilen JSON'da yapılması gereken değişiklikleri listele.
    
    Kullanıcı İsteği: "{user_input}"
    
    Hedef JSON:
    {current_values}
    
    KATI KURALLAR (Strict Mode):
    1. Cevabın SADECE geçerli bir JSON listesi olsun: [ {{"path": "...", "value": ...}} ]
    2. EĞER İSTENEN DEĞER GEÇERSİZSE (Örn: 'memory' için 'banana', 'replicas' için 'high'), ASLA TAHMİN YAPMA. Boş liste [] döndür.
    3. Path, nokta (.) ile ayrılmış anahtarlardan oluşmalı.
    4. 'memory' (MB) ve 'cpu' (milliCPU) değerleri DAİMA tamsayı (integer) olmalıdır. 
       - "1gb" -> 1024 (limitMiB/requestMiB)
       - "500m" -> 500 (limitMilliCPU/requestMilliCPU)
       - "banana" -> GEÇERSİZ -> []
    5. Eğer kullanıcı anlamsız bir şey isterse (örn: "yapay zeka dünyayı ele geçirsin"), boş liste [] döndür.
    6. ASLA kök dizine veya mevcut olmayan yollara ekleme yapma.
    7. 'resources' (cpu/memory) değişikliklerini 'containers.<app_name>.resources' altına işle.
    
    Örnek Doğru Cevap:
    [
      {{"path": "workloads.statefulsets.tournament.replicas", "value": 3}}
    ]

    Örnek Hatalı İstek ("set memory to banana"):
    []

    Cevap:"""
    
    updated_json_str, err = query_ollama(UPDATE_PROMPT)
    if err:
        return jsonify({"error": f"AI failed to generate update: {err}"}), 500
    
    if not updated_json_str:
        return jsonify({"error": "AI returned empty response"}), 500

    # Clean up AI response (extract JSON list)
    try:
        # Simple extraction: find first [ and last ]
        start_index = updated_json_str.find('[')
        end_index = updated_json_str.rfind(']')
        
        if start_index != -1 and end_index != -1 and end_index > start_index:
            updated_json_str = updated_json_str[start_index : end_index + 1]
        
        changes = json.loads(updated_json_str)
        if not isinstance(changes, list):
             return jsonify({"error": "AI output must be a list of changes"}), 500

        if not changes:
             return jsonify({"error": "No changes determined. The request might be invalid or already satisfied."}), 400
             
        # Apply changes to original values COPY to validate first
        import copy
        temp_values = copy.deepcopy(values)
        
        for change in changes:
            path_keys = change['path'].split('.')
            new_value = change['value']
            
            # Validate Root Key
            if path_keys[0] not in values:
                print(f"Skipping invalid root key: {path_keys[0]}", flush=True)
                continue # Skip changes that try to add new root keys

            # Safety Filter: Prevent AI from adding memory/cpu/replicas to 'services'
            if path_keys[0] == 'services' and any(k in change['path'] for k in ['memory', 'cpu', 'replicas']):
                print(f"Skipping invalid resource/replica path in services: {change['path']}", flush=True)
                continue

            # Safety Filter: Prevent AI from adding 'envs' to deployment root (must be in containers)
            if 'envs' in change['path'] and 'containers' not in change['path']:
                print(f"Skipping invalid envs path (missing 'containers'): {change['path']}", flush=True)
                continue

            # Safety Filter: Prevent AI from adding 'resources' to deployment root (must be in containers)
            if 'resources' in change['path'] and 'containers' not in change['path']:
                print(f"Skipping invalid resources path (missing 'containers'): {change['path']}", flush=True)
                continue

            # Navigate to the correct location
            target = temp_values
            for key in path_keys[:-1]:
                target = target.setdefault(key, {})
            
            # Set the new value
            target[path_keys[-1]] = new_value

        # --- VALIDATE AGAINST SCHEMA ---
        try:
            print(f"Validating schema for {app_name}...", flush=True)
            jsonschema.validate(instance=temp_values, schema=schema)
            print("Validation successful.", flush=True)
        except jsonschema.exceptions.ValidationError as ve:
             return jsonify({"error": f"Schema Validation Failed: {ve.message}"}), 400
        # -------------------------------

        # --- SAVE CHANGES TO VALUES SERVER ---
        try:
            # We use the internal Docker DNS name 'values-server'
            # Updated to match new values-server endpoint
            save_url = f"{VALUES_SERVICE_URL}/{app_name}"
            # print(f"Saving to: {save_url}", flush=True)
            save_resp = requests.post(save_url, json=temp_values)
            save_resp.raise_for_status()
        except Exception as e:
            return jsonify({"error": f"Failed to save values: {str(e)}"}), 500
        # -------------------------------------

        return jsonify(temp_values)

    except json.JSONDecodeError:
         return jsonify({"error": f"AI produced invalid JSON: {updated_json_str}"}), 500
    except Exception as e:
         return jsonify({"error": f"Error applying changes: {str(e)}"}), 500

if __name__ == '__main__':
    host, port = args.listen.split(':')
    app.run(host=host, port=int(port))
