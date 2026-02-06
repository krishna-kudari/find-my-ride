"View files for service"

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.request import Request

from .services.uber import Uber
from .services.rapido import Rapido
from .services.ola import Ola


@api_view(["GET"])
def health(_request: Request):
    "health view function"
    return Response({"status": 200})


@api_view(["GET"])
def fares(request: Request):
    ""
    source = (12.912168, 77.6438711)
    destination = (12.9352403, 77.624532)
    response = {"uber": None, "rapido": None, "ola": None}
    try:
        result = Uber().fetch_prices(source, destination)
        if result is not None:
            response["uber"] = result
    except Exception:
        pass
    try:
        result = Rapido().fetch_prices(source, destination)
        if result is not None:
            response["rapido"] = result
    except Exception:
        pass

    try:
        result = Ola().fetch_prices(source, destination)
        if result is not None:
            response["ola"] = result
    except Exception:
        pass

    return Response({"status": "ok", "data": response})

@api_view(["GET"])
def get_fares_uber(request: Request):
    ""
    source = (12.912168, 77.6438711)
    destination = (12.9352403, 77.624532)

    result = Uber().fetch_prices(source, destination)

    return Response({"status": "ok", "data": result})


@api_view(["GET"])
def get_fares_rapido(request: Request):
    ""
    source = (12.912168, 77.6438711)
    destination = (12.9352403, 77.624532)

    result = Rapido().fetch_prices(source, destination)

    return Response({"status": "ok", "data": result})


@api_view(["GET"])
def get_fares_ola(request: Request):
    ""
    source = (12.912168, 77.6438711)
    destination = (12.9352403, 77.624532)

    result = Ola().fetch_prices(source, destination)

    return Response({"status": "ok", "data": result})
