from fastapi import Request

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # puede venir con varios IPs separados por coma
        return forwarded.split(",")[0].strip()
    return request.client.host

def get_client_device(request: Request) -> str:
    user_agent = request.headers.get("User-Agent", "Desconocido")
    if "Android" in user_agent:
        return "Android"
    elif "iPhone" in user_agent or "iPad" in user_agent:
        return "iOS"
    elif "Windows" in user_agent:
        return "Windows"
    elif "Mac" in user_agent:
        return "Mac"
    elif "Linux" in user_agent:
        return "Linux"
    else:
        return user_agent