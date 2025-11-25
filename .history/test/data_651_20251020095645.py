"""Sample payload for model 651 (Donation).
Fill in real testing data as a Python dict named 'payload'.
All comments and identifiers are in English. Messages returned by the API are in Spanish.
"""

payload = {
    "presenter": {
        "nif": "00000000T",
        "nombre": "Test",
        "primerApellido": "User",
        "domicilio": {
            "via": "Calle Ejemplo",
            "numero": "1",
            "cp": "28001",
            "municipio": "Madrid",
            "provincia": "Madrid",
            "pais": "ES",
        },
    },
    "donor": {
        "nif": "33333333S",
        "nombre": "Donor",
        "primerApellido": "Person",
        "esResidente": True,
    },
    "donees": [
        {
            "nif": "44444444K",
            "nombre": "Donee",
            "primerApellido": "One",
            "parentesco": "Hijo/a",
            "porcentajeParticipacionPct": 100,
            "esResidente": True,
        }
    ],
    "donations": [
        {
            "tipo": "dinero",
            "descripcion": "Cash donation",
            "valor": 5000,
            "fechaDonacion": "2024-10-10",
        }
    ],
    "documentacionNotarial": {
        "tipoDocumento": "privado",
    },
    "autoliquidation": {
        "formaPago": "otras",
    },
}



