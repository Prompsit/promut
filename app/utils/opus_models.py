import requests

def get_opus_model_info(lang1, lang2):
    url = f"https://opus.nlpl.eu/api/dashboardStats/{lang1}&{lang2}&bleu&flores200-devtest&opus"
    result = requests.get(url, timeout=60)
    models = result.json()["cleanData"]
    # they're ordered, so we just take the first opus model
    for model in models:
        if model["catalog"] == "OPUS":
            model_name = model["model"]
            download_link = "https://object.pouta.csc.fi/" + model_name + ".zip"
            model["download_link"] = download_link
            return model
    raise ValueError("No model found for the provided languages")