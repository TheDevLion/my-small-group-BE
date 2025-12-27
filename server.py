import os

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv("PORT", "5010"))
    app.run(port=port)
    #app.run(debug=True, host='127.0.0.1', port='5010')
