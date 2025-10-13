from flask import request, jsonify


def register_chat_routes(app):
    """
    Registers chat-related routes.
    """

    @app.route('/api/hello')
    def hello():
        return {"message": "Hello from backend!"}

    @app.route('/api/chat', methods=['POST'])
    def chat():
        """
        Handle chat messages sent by the client.

        Expects:
            Content-Type: application/json
            JSON body: { "prompt": "<user prompt>" }

        Returns:
            200: JSON { "response": "Response from AI" }
            400: JSON { "error": "Missing 'prompt'" } if input invalid
        """

        data = request.get_json()

        # Error 400
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing "prompt" in request body'}), 400

        user_prompt = data['prompt']

        mock_response = f"Response from backend to prompt: {user_prompt}"

        return jsonify({'response': mock_response})
