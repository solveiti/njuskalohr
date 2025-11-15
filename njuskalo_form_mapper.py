"""
Comprehensive form mapper for Njuskalo.hr with Slovenian to Croatian feature translation
Maps database content fields to Njuskalo form fields with intelligent recognition
"""

class NjuskaloFormMapper:
    """Maps content data to Njuskalo form fields with Slovenian-Croatian translation"""

    # Slovenian to Croatian feature translations
    FEATURE_TRANSLATIONS = {
        # From provided data - Slovenian features
        "Adaptive Cruise Control": ["adaptivni tempomat", "229542"],
        "Adaptive Headlights": ["prilagodljiva svjetla", "2660"],
        "Adjustable Pedals": None,  # Not available in Njuskalo
        "Aftermarket Wheels": None,  # Not available
        "Air Conditioning": ["klima uređaj", "66"],
        "Alloy Wheels": ["aluminijski naplatci", "41"],
        "ABS": ["ABS", "54"],

        # Sedeži - seats heating and controls
        "Sedeži - gretje spredaj": ["grijanje sjedala", "77"],
        "Sedeži - gretje zadaj": ["grijanje sjedala - straga", "78"],
        "Sedeži - električna nastavitev": ["električno podizanje sjedala", "80"],

        # Ostalo - other features
        "Organizator prtljažnega prostora": ["mrežasta pregrada prtljažnika", "52"],
        "Osvetlitev v vratih - zunaj": None,  # Not available
        "Ročni menjalnik": None,  # This is transmission type, not equipment
        "Kolesa: ostalo": None,  # Generic wheels
        "Krmiljenje vseh koles - 4WS": None,  # Not available
        "Ojačana zadnja os": None,  # Not available
    }

    # Croatian equipment mapping with checkbox IDs
    CROATIAN_EQUIPMENT_MAP = {
        # Dodatna oprema (Additional Equipment)
        "aluminijski naplatci": ("41", "additional_equipment"),
        "športsko podvozje": ("42", "additional_equipment"),
        "4x4": ("43", "additional_equipment"),
        "3. stop svjetlo": ("44", "additional_equipment"),
        "prednja svjetla za maglu": ("45", "additional_equipment"),
        "nadzor pritiska u pneumaticima": ("46", "additional_equipment"),
        "ksenonska svjetla": ("47", "additional_equipment"),
        "bi-ksenonska svjetla": ("48", "additional_equipment"),
        "LED svjetla": ("2659", "additional_equipment"),
        "prilagodljiva svjetla": ("2660", "additional_equipment"),
        "senzor za svjetlo": ("2661", "additional_equipment"),
        "senzor za kišu": ("2662", "additional_equipment"),
        "navigacija": ("49", "additional_equipment"),
        "navigacija + TV": ("50", "additional_equipment"),
        "putno računalo": ("51", "additional_equipment"),
        "mrežasta pregrada prtljažnika": ("52", "additional_equipment"),
        "krovni nosači": ("53", "additional_equipment"),
        "kuka za vuču": ("344", "additional_equipment"),
        "zatamnjena stakla": ("345", "additional_equipment"),
        "upravljač presvučen kožom": ("346", "additional_equipment"),
        "krovni prozor": ("347", "additional_equipment"),
        "krovna kutija": ("2663", "additional_equipment"),
        "Head-up display": ("2664", "additional_equipment"),
        "Start-stop sistem": ("2665", "additional_equipment"),
        "prilagođeno za invalide": ("2666", "additional_equipment"),

        # Sigurnost (Safety)
        "ABS": ("54", "safety_features"),
        "ESP": ("55", "safety_features"),
        "EDC": ("56", "safety_features"),
        "ETS": ("57", "safety_features"),
        "ASR": ("58", "safety_features"),
        "ASD": ("59", "safety_features"),
        "samozatezajući sigurnosni pojasevi": ("60", "safety_features"),
        "isofix (sustav vezanja sjedalice za dijete)": ("580", "safety_features"),
        "isofix": ("580", "safety_features"),
        "adaptivni tempomat": ("229542", "safety_features"),
        "tempomat s funkcijom kočenja": ("229425", "safety_features"),
        "sustav upozorenja na napuštanje prometne trake": ("229426", "safety_features"),
        "zadržavanje vozila u voznoj traci": ("229427", "safety_features"),
        "zaštita od stražnjeg naleta vozila": ("229428", "safety_features"),
        "zaštita od bočnog naleta vozila": ("229429", "safety_features"),

        # Komfor (Comfort)
        "centralno zaključavanje": ("63", "comfort_features"),
        "servo upravljač": ("64", "comfort_features"),
        "električni prozori": ("65", "comfort_features"),
        "klima uređaj": ("66", "comfort_features"),
        "automatska klima - jednokružna": ("67", "comfort_features"),
        "automatska klima - dvokružna": ("68", "comfort_features"),
        "automatska klima - trokružna": ("2652", "comfort_features"),
        "automatska klima - četverokružna": ("2653", "comfort_features"),
        "tempomat": ("69", "comfort_features"),
        "ograničivač brzine": ("70", "comfort_features"),
        "multimedija": ("2654", "comfort_features"),
        "MP3": ("71", "comfort_features"),
        "CD": ("72", "comfort_features"),
        "radio": ("73", "comfort_features"),
        "USB": ("2655", "comfort_features"),
        "AUX priključak": ("2656", "comfort_features"),
        "Bluetooth": ("2657", "comfort_features"),
        "daljinsko zaključavanje": ("74", "comfort_features"),
        "daljinsko upravljanje za multimediju": ("75", "comfort_features"),
        "grijanje vetrobranskog stakla": ("76", "comfort_features"),
        "grijanje sjedala": ("77", "comfort_features"),
        "grijanje sjedala - straga": ("78", "comfort_features"),
        "električno podešavanje retrovizora": ("79", "comfort_features"),
        "električno podizanje sjedala": ("80", "comfort_features"),
        "memorija podešavanja sjedala": ("81", "comfort_features"),
        "podešavanje visine sjedala": ("82", "comfort_features"),
        "podesiva potpora za leđa": ("83", "comfort_features"),
        "podesiva potpora za leđa - straga": ("84", "comfort_features"),
        "unutarnja oprema od drva": ("85", "comfort_features"),
        "kožna unutarnja oprema": ("86", "comfort_features"),
        "alarm": ("87", "comfort_features"),
    }

    # Fuel type mapping - Slovenian to Croatian
    FUEL_TYPE_MAP = {
        "DIESEL": {"croatian": "Diesel", "id": "1"},
        "Diesel": {"croatian": "Diesel", "id": "1"},
        "PETROL": {"croatian": "Benzin", "id": "2"},
        "Petrol": {"croatian": "Benzin", "id": "2"},
        "Benzin": {"croatian": "Benzin", "id": "2"},
        "HYBRID": {"croatian": "Hibrid", "id": "6"},
        "Hibrid": {"croatian": "Hibrid", "id": "6"},
        "ELECTRIC": {"croatian": "Električni", "id": "7"},
        "Električni": {"croatian": "Električni", "id": "7"},
        "HYBRID_DIESEL": {"croatian": "Hibrid-dizel", "id": "2654"},
        "HYBRID_PETROL": {"croatian": "Hibrid-benzin", "id": "2653"},
        "LPG": {"croatian": "Plin (LPG)", "id": "3"},
        "CNG": {"croatian": "Plin (CNG)", "id": "4"},
        "HYDROGEN": {"croatian": "Vodik", "id": "8"},
    }

    # Transmission type mapping
    TRANSMISSION_MAP = {
        "Automatic": {"croatian": "Automatski", "id": "14"},
        "Automatski": {"croatian": "Automatski", "id": "14"},
        "Manual": {"croatian": "Ručni", "id": "13"},
        "Ručni": {"croatian": "Ručni", "id": "13"},
        "Manualni": {"croatian": "Ručni", "id": "13"},
        "SEMI_AUTOMATIC": {"croatian": "Poluautomatski", "id": "15"},
    }

    # Drive type mapping - Slovenian to Croatian
    DRIVE_TYPE_MAP = {
        "FRONT": {"croatian": "Prednji", "id": "16"},
        "Prednji": {"croatian": "Prednji", "id": "16"},
        "REAR": {"croatian": "Stražnji", "id": "17"},
        "Stražnji": {"croatian": "Stražnji", "id": "17"},
        "BOTH": {"croatian": "4x4", "id": "18"},
        "4x4": {"croatian": "4x4", "id": "18"},
        "AWD": {"croatian": "4x4", "id": "18"},
        "4WD": {"croatian": "4x4", "id": "18"},
    }

    # Body type mapping
    BODY_TYPE_MAP = {
        "Limuzina": {"croatian": "Limuzina", "id": "19"},
        "Sedan": {"croatian": "Limuzina", "id": "19"},
        "Karavan": {"croatian": "Karavan", "id": "20"},
        "Wagon": {"croatian": "Karavan", "id": "20"},
        "Estate": {"croatian": "Karavan", "id": "20"},
        "Coupe": {"croatian": "Coupe/Sportski", "id": "21"},
        "Kabriolet": {"croatian": "Kabriolet", "id": "22"},
        "Convertible": {"croatian": "Kabriolet", "id": "22"},
        "Terensko": {"croatian": "Terensko", "id": "23"},
        "SUV": {"croatian": "Terensko", "id": "23"},
        "Gradsko": {"croatian": "Gradsko", "id": "24"},
        "Hatchback": {"croatian": "Gradsko", "id": "24"},
        "Monovolumen": {"croatian": "Monovolumen (MPV)", "id": "25"},
        "MPV": {"croatian": "Monovolumen (MPV)", "id": "25"},
        "Pickup": {"croatian": "Pickup", "id": "26"},
    }

    # Door count mapping
    DOOR_COUNT_MAP = {
        "2": {"croatian": "2/3 vrata", "id": "27"},
        "3": {"croatian": "2/3 vrata", "id": "27"},
        "4": {"croatian": "4/5 vrata", "id": "28"},
        "5": {"croatian": "4/5 vrata", "id": "28"},
    }

    # Color mapping
    COLOR_MAP = {
        # English colors
        "Black": "Crna",
        "White": "Bijela",
        "Silver": "Srebrna",
        "Gray": "Siva",
        "Grey": "Siva",
        "Red": "Crvena",
        "Blue": "Plava",
        "Green": "Zelena",
        "Yellow": "Žuta",
        "Orange": "Narančasta",
        "Brown": "Smeđa",
        "Beige": "Bež",
        "Gold": "Zlatna",
        "Purple": "Ljubičasta",

        # Slovenian colors
        "Črna": "Crna",
        "Bela": "Bijela",
        "Srebrna": "Srebrna",
        "Siva": "Siva",
        "Rdeča": "Crvena",
        "Modra": "Plava",
        "Zelena": "Zelena",
        "Rumena": "Žuta",
        "Oranžna": "Narančasta",
        "Rjava": "Smeđa",
    }

    @classmethod
    def map_features(cls, features_list):
        """
        Map Slovenian features to Croatian checkbox IDs

        Args:
            features_list: List of feature names in Slovenian or English

        Returns:
            dict: {category: [checkbox_ids]}
        """
        mapped_features = {
            "additional_equipment": [],
            "safety_features": [],
            "comfort_features": []
        }

        for feature in features_list:
            # First try direct translation
            if feature in cls.FEATURE_TRANSLATIONS:
                translated = cls.FEATURE_TRANSLATIONS[feature]
                if translated:
                    croatian_name, checkbox_id = translated
                    if croatian_name in cls.CROATIAN_EQUIPMENT_MAP:
                        checkbox_id, category = cls.CROATIAN_EQUIPMENT_MAP[croatian_name]
                        if checkbox_id not in mapped_features[category]:
                            mapped_features[category].append(checkbox_id)

            # Try direct match in Croatian equipment map
            elif feature in cls.CROATIAN_EQUIPMENT_MAP:
                checkbox_id, category = cls.CROATIAN_EQUIPMENT_MAP[feature]
                if checkbox_id not in mapped_features[category]:
                    mapped_features[category].append(checkbox_id)

            # Try fuzzy matching (case insensitive, partial match)
            else:
                feature_lower = feature.lower()
                for croatian_name, (checkbox_id, category) in cls.CROATIAN_EQUIPMENT_MAP.items():
                    if feature_lower in croatian_name.lower() or croatian_name.lower() in feature_lower:
                        if checkbox_id not in mapped_features[category]:
                            mapped_features[category].append(checkbox_id)
                        break

        return mapped_features

    @classmethod
    def map_fuel_type(cls, fuel_type):
        """Map fuel type to Croatian equivalent"""
        if fuel_type in cls.FUEL_TYPE_MAP:
            return cls.FUEL_TYPE_MAP[fuel_type]
        return {"croatian": fuel_type, "id": None}

    @classmethod
    def map_transmission(cls, transmission):
        """Map transmission type to Croatian equivalent"""
        if transmission in cls.TRANSMISSION_MAP:
            return cls.TRANSMISSION_MAP[transmission]
        return {"croatian": transmission, "id": None}

    @classmethod
    def map_drive_type(cls, drive_type):
        """Map drive type to Croatian equivalent"""
        if drive_type in cls.DRIVE_TYPE_MAP:
            return cls.DRIVE_TYPE_MAP[drive_type]
        return {"croatian": drive_type, "id": None}

    @classmethod
    def map_body_type(cls, body_type):
        """Map body type to Croatian equivalent"""
        if body_type in cls.BODY_TYPE_MAP:
            return cls.BODY_TYPE_MAP[body_type]
        return {"croatian": body_type, "id": None}

    @classmethod
    def map_door_count(cls, door_count):
        """Map door count to Croatian equivalent"""
        door_str = str(door_count)
        if door_str in cls.DOOR_COUNT_MAP:
            return cls.DOOR_COUNT_MAP[door_str]
        return {"croatian": door_str, "id": None}

    @classmethod
    def map_color(cls, color):
        """Map color to Croatian equivalent"""
        if color in cls.COLOR_MAP:
            return cls.COLOR_MAP[color]
        return color

    @classmethod
    def extract_contact_value(cls, data):
        """Extract first valid value from contact data (handles arrays)"""
        if isinstance(data, list):
            for item in data:
                if item and str(item).strip():
                    return str(item).strip()
            return ""
        return str(data) if data else ""
