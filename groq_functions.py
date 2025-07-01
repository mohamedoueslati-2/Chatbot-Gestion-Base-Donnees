import requests
import json
import re

def call_groq(messages, api_key, model="llama-3.1-8b-instant", temperature=0.7):
    if not api_key:
        return "Veuillez fournir une clé API Groq.", messages

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1000
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            data=json.dumps(data)
        )

        if response.status_code == 200:
            assistant_message = response.json()["choices"][0]["message"]["content"]
            messages.append({"role": "assistant", "content": assistant_message})
            return assistant_message, messages
        else:
            return f"Erreur : {response.status_code} - {response.text}", messages
    except Exception as e:
        return f"Erreur : {str(e)}", messages

groq_models = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
    "qwen-qwq-32b",
    "mistral-saba-24b"
]

def extract_sql_query(text):
    """Extraire la requête SQL du texte de réponse"""
    sql_patterns = [
        r'```sql\s*\n(.*?)\n```',
        r'```\s*\n(SELECT.*?)\n```',
        r'```\s*\n(INSERT.*?)\n```',
        r'```\s*\n(UPDATE.*?)\n```',
        r'```\s*\n(DELETE.*?)\n```',
    ]
    
    for pattern in sql_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            query = match.group(1).strip()
            # Vérifier que ce n'est pas une requête de structure
            if not re.match(r'^(CREATE|ALTER|DROP)\s+', query, re.IGNORECASE):
                return query
    
    # Chercher des requêtes sûres uniquement
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if re.match(r'^(SELECT|INSERT|UPDATE|DELETE)\s+', line, re.IGNORECASE):
            return line.strip()
    
    return None

def format_sql_result(result, query):
    """Formater les résultats SQL pour un affichage plus joli"""
    if not result or "Erreur" in result:
        return result
    
    # Si c'est un message de succès (INSERT, UPDATE, DELETE)
    if "Requête exécutée avec succès" in result:
        return f"✅ **{result}**"
    
    try:
        lines = result.strip().split('\n')
        if len(lines) < 2:
            return result
        
        # Séparer les colonnes et les données
        headers = lines[0].split(', ')
        rows = [line.split(', ') for line in lines[1:]]
        
        # Créer un tableau markdown
        markdown_table = "### 📊 Résultats de la requête\n\n"
        
        # En-têtes
        markdown_table += "| " + " | ".join(headers) + " |\n"
        markdown_table += "|" + "---|" * len(headers) + "\n"
        
        # Données (limiter à 50 lignes pour l'affichage)
        max_rows = min(50, len(rows))
        for i, row in enumerate(rows[:max_rows]):
            # S'assurer que chaque ligne a le bon nombre de colonnes
            while len(row) < len(headers):
                row.append("")
            markdown_table += "| " + " | ".join(str(cell) for cell in row[:len(headers)]) + " |\n"
        
        # Ajouter info si tronqué
        if len(rows) > max_rows:
            markdown_table += f"\n*... et {len(rows) - max_rows} autres lignes*"
        
        markdown_table += f"\n\n**📈 Total: {len(rows)} ligne(s)**"
        
        return markdown_table
        
    except Exception as e:
        return f"Résultat:\n```\n{result}\n```"

def clear_conversation(schema_text="", custom_role="", custom_rules=""):
    # Rôle par défaut
    default_role = "Tu es un assistant expert en base de données MySQL."
    
    # Règles par défaut
    default_rules = """RÈGLES IMPORTANTES :
- Réponds SEULEMENT avec la requête SQL demandée
- N'ajoute JAMAIS de CREATE TABLE, ALTER TABLE ou autres commandes de structure
- Utilise UNIQUEMENT SELECT, INSERT, UPDATE, DELETE sur les tables existantes
- Encadre toujours ta requête avec ```sql et ```
- Sois précis et concis
- afficher les lignes des tables affectées par la requête
- Si la requête est trop complexe, demande des précisions à l'utilisateur
- Si l'utilisateur demande la structure de la base, affiche-la clairement"""
    
    # Utiliser les valeurs personnalisées si fournies, sinon les valeurs par défaut
    role = custom_role.strip() if custom_role.strip() else default_role
    rules = custom_rules.strip() if custom_rules.strip() else default_rules
    
    return [{
        "role": "system",
        "content": f"""
{role}
Tu génères des requêtes SQL basées sur le schéma suivant :

{schema_text}

{rules}

Exemple :
Question: "Montre tous les produits"
Réponse: 
```sql
SELECT * FROM produit;
```

NE JAMAIS générer de requêtes CREATE, ALTER, DROP !
        """.strip()
    }]