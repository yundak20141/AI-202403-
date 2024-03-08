import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google.api_core.client_options import ClientOptions
from google.cloud.discoveryengine_v1alpha import SearchServiceClient, SearchRequest

import config

app = Flask(__name__)
line_api = LineBotApi(config.token)
webhook_handler = WebhookHandler(config.secret)

PROJECT = config.project_id
LOCATION = config.location
DATA_STORE = config.datastore

def create_search_client():
    client_options = ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com") if LOCATION != "global" else None
    return SearchServiceClient(client_options=client_options)

def get_file_name(file_link: str) -> str:
    return file_link.split('/')[-1]

def perform_search(client, user_query: str) -> str:
    serving_config = client.serving_config_path(
        project=PROJECT,
        location=LOCATION,
        data_store=DATA_STORE,
        serving_config="default_config",
    )
    
    search_request = SearchRequest(
        serving_config=serving_config,
        query=user_query,
        page_size=5,
        content_search_spec=SearchRequest.ContentSearchSpec(
            summary_spec=SearchRequest.ContentSearchSpec.SummarySpec(
                summary_result_count=5,
                ignore_non_summary_seeking_query=True,
                ignore_adversarial_query=True,
                model_spec=SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                    version="preview"
                )
            ),
            extractive_content_spec=SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                max_extractive_answer_count=1
            )
        )
    )
    
    search_response = client.search(search_request)
    app.logger.info(f"Vertex AI search response: {search_response}")
    
    summary = search_response.summary.summary_text if search_response.summary else "No relevant results found."
    
    file_names = [get_file_name(result.document.derived_struct_data["link"]) for result in search_response.results] if search_response.results else []
    
    response_text = summary
    if file_names:
        response_text += "\n\n関連文書のパス:\n" + "\n".join(file_names)
    
    return response_text

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info(f"Received request body: {body}")
    
    try:
        webhook_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@webhook_handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_query = event.message.text
    search_client = create_search_client()
    response_text = perform_search(search_client, user_query)
    
    try:
        line_api.reply_message(event.reply_token, TextSendMessage(text=response_text))
    except Exception as e:
        app.logger.error(f"Failed to send reply message: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)