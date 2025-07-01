import gradio as gr
from groq_functions import groq_models, clear_conversation
from mysql_functions import *

def create_interface():
    with gr.Blocks(title="Groq + MySQL Assistant") as app:
        gr.Markdown("# 🧠 Interface IA (Groq) + Gestion Base MySQL")
        
        mysql_config = gr.State({})
        stored_custom_role = gr.State("")
        stored_custom_rules = gr.State("")
        
        with gr.Tab("💬 Assistant SQL IA"):
            conversation_state = gr.State(clear_conversation())

            with gr.Row():
                with gr.Column(scale=1):
                    api_key = gr.Textbox(label="Clé API Groq", type="password")
                    model = gr.Dropdown(choices=groq_models, value="llama-3.1-8b-instant", label="Modèle")
                    temperature = gr.Slider(minimum=0.0, maximum=1.0, value=0.7, step=0.1, label="Température")
                    auto_execute = gr.Checkbox(label="Exécuter automatiquement les requêtes SQL", value=True)
                    
                    # Nouveaux champs pour personnaliser le rôle et les règles
                    with gr.Accordion("🎭 Personnalisation du rôle et des règles", open=False):
                        custom_role = gr.Textbox(
                            label="Rôle personnalisé (optionnel)", 
                            lines=2, 
                            placeholder="Ex: Tu es un assistant spécialisé en analyse de données commerciales...",
                            info="Laissez vide pour utiliser le rôle par défaut"
                        )
                        custom_rules = gr.Textbox(
                            label="Règles personnalisées (optionnelles)", 
                            lines=6, 
                            placeholder="Ex: - Privilégie les requêtes avec des JOINs\n- Ajoute toujours des commentaires\n- Utilise des alias pour les tables...",
                            info="Laissez vide pour utiliser les règles par défaut"
                        )
                        update_settings_btn = gr.Button("📝 Appliquer les nouveaux paramètres")
                    
                    gr.Markdown("💡 *Configurez la base de données dans l'onglet 'Base MySQL'*")
                    clear_btn = gr.Button("🧹 Réinitialiser le Chat")

                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(label="Conversation", height=400, bubble_full_width=False)
                    msg = gr.Textbox(label="Votre question", lines=2, placeholder="Ex: Montre-moi tous les utilisateurs ou 'structure' pour voir les tables")
                    submit_btn = gr.Button("Envoyer")

            # Fonction pour appliquer les nouveaux paramètres
            def apply_custom_settings(role, rules, mysql_conf):
                schema_text = ""
                if mysql_conf and mysql_conf.get("host") and mysql_conf.get("user") and mysql_conf.get("db_name"):
                    schema_text = get_db_schema(mysql_conf["host"], mysql_conf["user"], mysql_conf["password"], mysql_conf["db_name"])
                
                new_conversation = clear_conversation(schema_text, role, rules)
                return new_conversation, role, rules

            update_settings_btn.click(
                fn=apply_custom_settings,
                inputs=[custom_role, custom_rules, mysql_config],
                outputs=[conversation_state, stored_custom_role, stored_custom_rules]
            )

            submit_btn.click(
                fn=groq_chat_interface,
                inputs=[msg, chatbot, api_key, model, temperature, conversation_state, auto_execute, mysql_config],
                outputs=[chatbot, conversation_state]
            ).then(lambda _: "", inputs=[msg], outputs=[msg])

            msg.submit(
                fn=groq_chat_interface,
                inputs=[msg, chatbot, api_key, model, temperature, conversation_state, auto_execute, mysql_config],
                outputs=[chatbot, conversation_state]
            ).then(lambda _: "", inputs=[msg], outputs=[msg])

            def clear_chat_with_custom_settings(role, rules, mysql_conf):
                schema_text = ""
                if mysql_conf and mysql_conf.get("host") and mysql_conf.get("user") and mysql_conf.get("db_name"):
                    schema_text = get_db_schema(mysql_conf["host"], mysql_conf["user"], mysql_conf["password"], mysql_conf["db_name"])
                
                new_conversation = clear_conversation(schema_text, role, rules)
                return [], new_conversation

            clear_btn.click(
                fn=clear_chat_with_custom_settings,
                inputs=[stored_custom_role, stored_custom_rules, mysql_config],
                outputs=[chatbot, conversation_state]
            )

            # Synchroniser les paramètres personnalisés
            custom_role.change(lambda x: x, inputs=[custom_role], outputs=[stored_custom_role])
            custom_rules.change(lambda x: x, inputs=[custom_rules], outputs=[stored_custom_rules])

        with gr.Tab("🗃️ Base MySQL"):
            with gr.Row():
                host = gr.Textbox(label="Hôte", value="localhost")
                user = gr.Textbox(label="Utilisateur")
                password = gr.Textbox(label="Mot de passe", type="password")
            btn = gr.Button("Lister les bases")
            db_list = gr.Dropdown(label="Bases disponibles", choices=[], interactive=True)
            schema_box = gr.Textbox(label="Structure de la base", lines=12, interactive=False)

            btn.click(update_db_list, inputs=[host, user, password], outputs=db_list)
            
            def schema_and_reset_with_stored_settings(host, user, password, db_name, role, rules):
                return schema_and_reset_chat(host, user, password, db_name, role, rules)
            
            db_list.change(
                schema_and_reset_with_stored_settings, 
                inputs=[host, user, password, db_list, stored_custom_role, stored_custom_rules], 
                outputs=[schema_box, conversation_state, mysql_config]
            )

            gr.Markdown("### 🧾 Exécuter une requête SQL")
            requete = gr.Textbox(label="Requête SQL", lines=3, placeholder="SELECT * FROM ma_table;")
            exec_btn = gr.Button("Exécuter")
            resultat = gr.Markdown(label="Résultat", value="")

            exec_btn.click(
                executer_requete_avec_format,
                inputs=[host, user, password, db_list, requete],
                outputs=resultat
            )

    return app