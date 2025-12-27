from flask import Blueprint, request
from flask_cors import cross_origin
import requests


stock_bp = Blueprint("stock", __name__)


@stock_bp.route("/stock_price", methods=["GET"])
@cross_origin(supports_credentials=True)
def get_stock_price():
    ticker = request.args.get("stock", "").lower()

    names = {
        "sapr4": "sanepar",
        "vale3": "vale",
        "goau4": "gerdau-met",
        "taee4": "taesa",
        "sanb4": "santander-br",
        "bbas3": "banco-do-brasil",
        "mglu3": "magazine-luiza",
        "klbn4": "klabin",
        "cple6": "copel",
    }

    r = requests.get(f"https://www.infomoney.com.br/cotacoes/b3/acao/{names[ticker]}-{ticker}/".replace("@stock", ticker))

    beforeClosingValue = r.text.lower().split("fechamento anterior")[1][:20].replace("<td>", "").replace("</td>", "").replace("\n", "")
    dayOpeningValue = r.text.lower().split("abertura")[1][:20].replace("<td>", "").replace("</td>", "").replace("\n", "")
    currentPrice = r.text.lower().split("reais (brl - r$)")[0][-80:].replace("<td>", "").replace("</td>", "").replace("\n", "").replace("<p>", "").replace(" ", "").replace("</p>", "").replace("<label>", "").replace("</label>", "")
    
    return {
        "currentPrice": currentPrice,
        "beforeClosingValue": beforeClosingValue,
        "dayOpeningValue": dayOpeningValue,
    }
