import time
import requests
from datetime import datetime, timezone

# --- CREDENCIALES DE TELEGRAM ---
TELEGRAM_BOT_TOKEN = "8689455719:AAHcO8c0Z7FqqNiSMEdfhbb54My15203nww"
# NOTA: Reemplaza este valor con tu Chat ID numérico privado (obtenido de @userinfobot)
CHAT_ID = "8689455719"

# API ENDPOINTS DE DEXSCREENER
DEXSCREENER_BOOSTS_URL = "https://api.dexscreener.com/token-boosts/latest/v1"
DEXSCREENER_PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
DEXSCREENER_PAIRS_URL = "https://api.dexscreener.com/latest/dex/tokens/"

# Control de duplicados para no enviar la misma alerta dos veces
processed_boosts = set()
processed_profiles = set()

def send_telegram_message(message):
    """Envía la alerta formateada a tu bot de Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")

def get_token_details(token_address):
    """Obtiene datos detallados del token (precio, red, DEX y fecha de creación)."""
    try:
        res = requests.get(f"{DEXSCREENER_PAIRS_URL}{token_address}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            pairs = data.get("pairs", [])
            if not pairs:
                return None
            
            # Filtrar pares exclusivos de Solana / pump.fun / PumpSwap
            sol_pairs = [
                p for p in pairs 
                if p.get("chainId") == "solana" and 
                any(dex in p.get("dexId", "").lower() for dex in ["pump", "pumpswap", "pumpfun"])
            ]
            
            if not sol_pairs:
                return None
            
            # Tomar el par con mayor liquidez/relevancia
            pair = sol_pairs[0]
            created_at_ms = pair.get("pairCreatedAt", 0)
            if not created_at_ms:
                return None
            
            # Calcular la edad del token en horas
            now_ms = datetime.now(timezone.utc).timestamp() * 1000
            age_hours = (now_ms - created_at_ms) / (1000 * 3600)
            
            return {
                "name": pair.get("baseToken", {}).get("name", "Desconocido"),
                "symbol": pair.get("baseToken", {}).get("symbol", "N/A"),
                "price_usd": pair.get("priceUsd", "0.00"),
                "dex": pair.get("dexId", "pump.fun").capitalize(),
                "url": pair.get("url", f"https://dexscreener.com/solana/{token_address}"),
                "age_hours": age_hours
            }
    except Exception as e:
        print(f"Error consultando el par {token_address}: {e}")
    return None

def check_boosted_tokens():
    """Rastrea tokens con 500 a 1000 boosts y edad menor a 10 horas."""
    try:
        res = requests.get(DEXSCREENER_BOOSTS_URL, timeout=10)
        if res.status_code == 200:
            boosts = res.json()
            for item in boosts:
                token_address = item.get("tokenAddress")
                amount = item.get("totalAmount", 0)
                chain = item.get("chainId", "")

                # Filtro de red Solana y rango de 500 a 1000 boosts
                if chain == "solana" and 500 <= amount <= 1000:
                    event_id = f"{token_address}_{amount}"
                    if event_id in processed_boosts:
                        continue
                    
                    token_info = get_token_details(token_address)
                    if token_info and token_info["age_hours"] <= 10:
                        msg = (
                            f"🚀 *Alerta de Boosted*\n"
                            f"🏷️ `memecoin con apoyo a anuncio`\n\n"
                            f"📌 *Nombre:* {token_info['name']} ({token_info['symbol']})\n"
                            f"💵 *Precio USD:* ${token_info['price_usd']}\n"
                            f"🔥 *Boosts:* {amount}\n"
                            f"🌐 *Red/DEX:* Solana / {token_info['dex']}\n"
                            f"⏱️ *Edad:* {token_info['age_hours']:.1f} horas\n\n"
                            f"🔗 [Ver en Dexscreener]({token_info['url']})"
                        )
                        send_telegram_message(msg)
                        processed_boosts.add(event_id)
    except Exception as e:
        print(f"Error verificando Boosted: {e}")

def check_profile_tokens():
    """Rastrea tokens con perfil actualizado de pump.fun con edad menor a 10 horas."""
    try:
        res = requests.get(DEXSCREENER_PROFILES_URL, timeout=10)
        if res.status_code == 200:
            profiles = res.json()
            for item in profiles:
                token_address = item.get("tokenAddress")
                chain = item.get("chainId", "")

                if chain == "solana" and token_address not in processed_profiles:
                    token_info = get_token_details(token_address)
                    if token_info and token_info["age_hours"] <= 10:
                        msg = (
                            f"📣 *Alerta de Profile*\n"
                            f"🏷️ `memecoin con comunidad`\n\n"
                            f"📌 *Nombre:* {token_info['name']} ({token_info['symbol']})\n"
                            f"💵 *Precio USD:* ${token_info['price_usd']}\n"
                            f"🌐 *Red/DEX:* Solana / {token_info['dex']}\n"
                            f"⏱️ *Edad:* {token_info['age_hours']:.1f} horas\n\n"
                            f"🔗 [Ver en Dexscreener]({token_info['url']})"
                        )
                        send_telegram_message(msg)
                        processed_profiles.add(token_address)
    except Exception as e:
        print(f"Error verificando Profiles: {e}")

if __name__ == "__main__":
    print("Bot activo y monitoreando Dexscreener 24/7...")
    while True:
        check_boosted_tokens()
        check_profile_tokens()
        time.sleep(15)  # Escanea la API cada 15 segundos

