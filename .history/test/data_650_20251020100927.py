"""Sample payload for model 650 (Succession).
Fill in real testing data as a Python dict named 'payload'.
All comments and identifiers are in English. Messages returned by the API are in Spanish.
"""

# Minimal skeleton to start testing. Replace placeholder values.
payload = {
    "presenter": {
        "nif": "00000000T",
        "nombre": "Test",
        "primerApellido": "User",
        "segundoApellido": None,
        "email": None,
        "telefono": None,
        "domicilio": {
            "via": "Calle Ejemplo",
            "numero": "1",
            "piso": None,
            "cp": "28001",
            "municipio": "Madrid",
            "provincia": "Madrid",
            "pais": "ES",
        },
    },
    "decedent": { # Causante
        "nif": "11111111H",
        "nombre": "Decedent",
        "primerApellido": "Example",
        "fechaFallecimiento": "2024-10-10",
        "caDevengo": "Madrid",
    },
    "heirs": [
        {
            "nif": "22222222J",
            "nombre": "Heir",
            "primerApellido": "One",
            "parentesco": "Hijo/a",
            "porcentajeParticipacionPct": 100,
        }
    ],
    "assets": [
        {
            "tipo": "inmuebles",
            "descripcion": "Flat",
            "valor": 100000,
            "cargasODebenes": 0,
            "esViviendaHabitual": False,
            "porcentajeTitularidadDecujusPct": 100,
        }
    ],
    "autoliquidation": {
        "formaPago": "otras",
        # Add 'iban' if formaPago = 'domiciliacion'
        # Add 'nrc' if formaPago = 'nrc'
    },
}


