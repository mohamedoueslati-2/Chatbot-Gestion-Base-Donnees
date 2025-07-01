import mysql.connector
import gradio as gr
from groq_functions import call_groq, extract_sql_query, format_sql_result, clear_conversation

def get_db_schema(host, user, password, db_name):
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        cur = conn.cursor(dictionary=True)
        
        cur.execute("""
            SELECT 
                c.TABLE_NAME, 
                c.COLUMN_NAME, 
                c.COLUMN_TYPE, 
                c.IS_NULLABLE,
                c.COLUMN_DEFAULT, 
                c.EXTRA, 
                c.COLUMN_KEY,
                tc.CONSTRAINT_TYPE,
                kcu.REFERENCED_TABLE_NAME, 
                kcu.REFERENCED_COLUMN_NAME,
                c.COLUMN_COMMENT
            FROM information_schema.COLUMNS c
            LEFT JOIN information_schema.KEY_COLUMN_USAGE kcu
              ON c.TABLE_SCHEMA = kcu.TABLE_SCHEMA 
              AND c.TABLE_NAME = kcu.TABLE_NAME
              AND c.COLUMN_NAME = kcu.COLUMN_NAME
            LEFT JOIN information_schema.TABLE_CONSTRAINTS tc
              ON tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA 
              AND tc.TABLE_NAME = kcu.TABLE_NAME
              AND tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE c.TABLE_SCHEMA = %s
            ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;
        """, (db_name,))
        
        tables = {}
        for row in cur.fetchall():
            table_name = row["TABLE_NAME"]
            if table_name not in tables:
                tables[table_name] = {
                    "columns": [],
                    "primary_keys": [],
                    "foreign_keys": []
                }
            
            col_info = f"{row['COLUMN_NAME']} {row['COLUMN_TYPE']}"
            
            if row['IS_NULLABLE'] == 'NO':
                col_info += " NOT NULL"
            
            if row['COLUMN_DEFAULT'] is not None:
                col_info += f" DEFAULT {row['COLUMN_DEFAULT']}"
            
            if row['EXTRA'] and 'auto_increment' in row['EXTRA'].lower():
                col_info += " AUTO_INCREMENT"
            
            if row['COLUMN_KEY'] == 'PRI' or row['CONSTRAINT_TYPE'] == 'PRIMARY KEY':
                col_info += " PRIMARY KEY"
                if row['COLUMN_NAME'] not in tables[table_name]["primary_keys"]:
                    tables[table_name]["primary_keys"].append(row['COLUMN_NAME'])
            
            if row['CONSTRAINT_TYPE'] == 'FOREIGN KEY':
                col_info += f" REFERENCES {row['REFERENCED_TABLE_NAME']}({row['REFERENCED_COLUMN_NAME']})"
                fk_info = {
                    "column": row['COLUMN_NAME'],
                    "references": f"{row['REFERENCED_TABLE_NAME']}({row['REFERENCED_COLUMN_NAME']})"
                }
                if fk_info not in tables[table_name]["foreign_keys"]:
                    tables[table_name]["foreign_keys"].append(fk_info)
            
            if row['COLUMN_COMMENT']:
                col_info += f" -- {row['COLUMN_COMMENT']}"
            
            tables[table_name]["columns"].append(col_info)
        
        cur.close()
        conn.close()
        
        # Format simplifié et clair pour l'IA
        schema_text = f"DATABASE: {db_name}\n\n"
        
        for table_name, table_info in tables.items():
            schema_text += f"TABLE {table_name}:\n"
            
            # Colonnes avec leurs types
            for col in table_info["columns"]:
                schema_text += f"  {col}\n"
            
            schema_text += "\n"
        
        return schema_text.strip()
        
    except Exception as e:
        return f"Erreur lors de la récupération du schéma : {e}"

def get_db_schema_for_display(host, user, password, db_name):
    """Version pour affichage complet de la structure au chatbot"""
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        cur = conn.cursor(dictionary=True)
        
        cur.execute("""
            SELECT 
                c.TABLE_NAME, 
                c.COLUMN_NAME, 
                c.COLUMN_TYPE, 
                c.IS_NULLABLE,
                c.COLUMN_DEFAULT, 
                c.EXTRA, 
                c.COLUMN_KEY,
                tc.CONSTRAINT_TYPE,
                kcu.REFERENCED_TABLE_NAME, 
                kcu.REFERENCED_COLUMN_NAME,
                c.COLUMN_COMMENT
            FROM information_schema.COLUMNS c
            LEFT JOIN information_schema.KEY_COLUMN_USAGE kcu
              ON c.TABLE_SCHEMA = kcu.TABLE_SCHEMA 
              AND c.TABLE_NAME = kcu.TABLE_NAME
              AND c.COLUMN_NAME = kcu.COLUMN_NAME
            LEFT JOIN information_schema.TABLE_CONSTRAINTS tc
              ON tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA 
              AND tc.TABLE_NAME = kcu.TABLE_NAME
              AND tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE c.TABLE_SCHEMA = %s
            ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;
        """, (db_name,))
        
        tables = {}
        for row in cur.fetchall():
            table_name = row["TABLE_NAME"]
            if table_name not in tables:
                tables[table_name] = []
            
            # Construire l'information de la colonne
            constraints = []
            if row['IS_NULLABLE'] == 'NO':
                constraints.append("NOT NULL")
            if row['COLUMN_KEY'] == 'PRI' or row['CONSTRAINT_TYPE'] == 'PRIMARY KEY':
                constraints.append("PRIMARY KEY")
            if row['EXTRA'] and 'auto_increment' in row['EXTRA'].lower():
                constraints.append("AUTO_INCREMENT")
            if row['CONSTRAINT_TYPE'] == 'FOREIGN KEY':
                constraints.append(f"FK → {row['REFERENCED_TABLE_NAME']}.{row['REFERENCED_COLUMN_NAME']}")
            if row['COLUMN_DEFAULT'] is not None:
                constraints.append(f"DEFAULT {row['COLUMN_DEFAULT']}")
            
            constraint_text = ', '.join(constraints) if constraints else ""
            comment_text = row['COLUMN_COMMENT'] if row['COLUMN_COMMENT'] else ""
            
            col_info = {
                'name': row['COLUMN_NAME'],
                'type': row['COLUMN_TYPE'],
                'constraints': constraint_text,
                'comment': comment_text
            }
            
            tables[table_name].append(col_info)
        
        cur.close()
        conn.close()
        
        # Construire l'affichage markdown complet
        display_text = f"# 📊 Structure de la base de données: **{db_name}**\n\n"
        
        for table_name, columns in tables.items():
            display_text += f"## 📋 Table: **{table_name}**\n\n"
            display_text += "| Colonne | Type | Contraintes | Commentaire |\n"
            display_text += "|---------|------|-------------|-------------|\n"
            
            for col in columns:
                display_text += f"| {col['name']} | {col['type']} | {col['constraints']} | {col['comment']} |\n"
            
            display_text += "\n---\n\n"
        
        return display_text
        
    except Exception as e:
        return f"❌ **Erreur lors de la récupération du schéma:** {e}"

def update_db_list(host, user, password):
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password
        )
        cur = conn.cursor()
        cur.execute("SHOW DATABASES;")
        dbs = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return gr.update(choices=dbs, value=dbs[0] if dbs else None)
    except Exception as e:
        return gr.update(choices=[], value=None, label=f"Erreur MySQL: {e}")

def schema_and_reset_chat(host, user, password, db_name, custom_role="", custom_rules=""):
    schema = get_db_schema(host, user, password, db_name)
    conversation = clear_conversation(schema, custom_role, custom_rules)
    mysql_config = {"host": host, "user": user, "password": password, "db_name": db_name}
    return schema, conversation, mysql_config

def executer_requete(host, user, password, db_name, requete):
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        cur = conn.cursor()
        cur.execute(requete)
        if cur.description:
            colonnes = [desc[0] for desc in cur.description]
            resultats = cur.fetchall()
            res = [", ".join(colonnes)] + [", ".join(str(x) for x in row) for row in resultats]
            retour = "\n".join(res)
        else:
            conn.commit()
            retour = f"Requête exécutée avec succès ({cur.rowcount} lignes affectées)"
        cur.close()
        conn.close()
        return retour
    except Exception as e:
        return f"Erreur : {e}"

def executer_requete_avec_format(host, user, password, db_name, requete):
    """Version avec formatage joli pour l'onglet MySQL"""
    result = executer_requete(host, user, password, db_name, requete)
    return format_sql_result(result, requete)

def groq_chat_interface(message, chat_history, api_key, model, temperature, conversation_state, auto_execute, mysql_config):
    if not conversation_state or len(conversation_state) == 0:
        conversation_state = clear_conversation()

    # Vérifier si l'utilisateur demande la structure
    if any(keyword in message.lower() for keyword in ['structure', 'schéma', 'schema', 'tables', 'affiche les tables', 'montre les tables', 'structure de la base']):
        if mysql_config and mysql_config.get("host") and mysql_config.get("user") and mysql_config.get("db_name"):
            try:
                structure_display = get_db_schema_for_display(
                    mysql_config["host"], 
                    mysql_config["user"], 
                    mysql_config["password"], 
                    mysql_config["db_name"]
                )
                chat_history.append((message, structure_display))
                return chat_history, conversation_state
            except Exception as e:
                error_msg = f"❌ **Erreur:** {str(e)}"
                chat_history.append((message, error_msg))
                return chat_history, conversation_state
        else:
            error_msg = "⚠️ **Veuillez d'abord configurer la base de données dans l'onglet 'Base MySQL'**"
            chat_history.append((message, error_msg))
            return chat_history, conversation_state

    conversation_state.append({"role": "user", "content": message})
    response, updated_conversation = call_groq(conversation_state, api_key, model, temperature)
    
    # Si l'exécution automatique est activée et qu'il y a une requête SQL
    if auto_execute and mysql_config and mysql_config.get("host") and mysql_config.get("user") and mysql_config.get("db_name"):
        sql_query = extract_sql_query(response)
        if sql_query:
            try:
                result = executer_requete(
                    mysql_config["host"], 
                    mysql_config["user"], 
                    mysql_config["password"], 
                    mysql_config["db_name"], 
                    sql_query
                )
                
                # Formater le résultat de manière plus jolie
                formatted_result = format_sql_result(result, sql_query)
                response += f"\n\n{formatted_result}"
                updated_conversation[-1]["content"] = response
                
            except Exception as e:
                response += f"\n\n❌ **Erreur lors de l'exécution:** {str(e)}"
                updated_conversation[-1]["content"] = response
    
    chat_history.append((message, response))
    return chat_history, updated_conversation