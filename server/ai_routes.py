from flask import Blueprint, request, Response, current_app, jsonify
from flask_jwt_extended import jwt_required

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')


@ai_bp.route('/route', methods=['POST'])
@jwt_required()
def ai_route():
    ai_service = current_app.config['AI_SERVICE']
    data = request.json
    print(data)

    query = data.get('query')
    result = ai_service.route_intent(query)
    return jsonify({"result": result})


@ai_bp.route('/chat', methods=['POST'])
@jwt_required()
def ai_chat():
    ai_service = current_app.config['AI_SERVICE']
    data = request.json
    messages = data.get('messages')
    print(messages)
    # 返回 Flask 的流式响应
    return Response(
        ai_service.chat_stream_generator(messages),
        mimetype='text/event-stream'
    )