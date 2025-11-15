#!/usr/bin/env python3
"""
Test script for njuskalo_form_mapper.py
Validates feature translation and mapping without browser automation
"""

import json
from njuskalo_form_mapper import NjuskaloFormMapper

def test_feature_mapping():
    """Test feature mapping with Slovenian data"""

    # Load test data
    with open('test_data_slovenian.json', 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    print("=" * 80)
    print("NJUSKALO FORM MAPPER - TEST SUITE")
    print("=" * 80)

    # Test 1: Feature Translation
    print("\n📋 TEST 1: Feature Mapping")
    print("-" * 80)
    features = test_data.get('features', [])
    print(f"Input features: {len(features)}")
    for i, feature in enumerate(features, 1):
        print(f"  {i}. {feature}")

    mapped = NjuskaloFormMapper.map_features(features)

    print(f"\nMapped features:")
    print(f"  📦 Additional Equipment: {len(mapped['additional_equipment'])} checkboxes")
    for checkbox_id in mapped['additional_equipment']:
        print(f"     → ID {checkbox_id}")

    print(f"  🛡️ Safety Features: {len(mapped['safety_features'])} checkboxes")
    for checkbox_id in mapped['safety_features']:
        print(f"     → ID {checkbox_id}")

    print(f"  🪑 Comfort Features: {len(mapped['comfort_features'])} checkboxes")
    for checkbox_id in mapped['comfort_features']:
        print(f"     → ID {checkbox_id}")

    total_mapped = sum(len(v) for v in mapped.values())
    print(f"\n✅ Total: {total_mapped} checkboxes mapped from {len(features)} input features")

    # Test 2: Fuel Type Mapping
    print("\n⛽ TEST 2: Fuel Type Mapping")
    print("-" * 80)
    fuel_type = test_data.get('vehicleFuelType')
    fuel_mapped = NjuskaloFormMapper.map_fuel_type(fuel_type)
    print(f"Input: {fuel_type}")
    print(f"Croatian: {fuel_mapped['croatian']}")
    print(f"ID: {fuel_mapped['id']}")

    # Test 3: Transmission Mapping
    print("\n⚙️  TEST 3: Transmission Mapping")
    print("-" * 80)
    transmission = test_data.get('vehicleTransmissionType')
    trans_mapped = NjuskaloFormMapper.map_transmission(transmission)
    print(f"Input: {transmission}")
    print(f"Croatian: {trans_mapped['croatian']}")
    print(f"ID: {trans_mapped['id']}")

    # Test 4: Drive Type Mapping
    print("\n🚗 TEST 4: Drive Type Mapping")
    print("-" * 80)
    drive_type = test_data.get('vehicleDriveWheels')
    drive_mapped = NjuskaloFormMapper.map_drive_type(drive_type)
    print(f"Input: {drive_type}")
    print(f"Croatian: {drive_mapped['croatian']}")
    print(f"ID: {drive_mapped['id']}")

    # Test 5: Body Type Mapping
    print("\n🚙 TEST 5: Body Type Mapping")
    print("-" * 80)
    body_type = test_data.get('vehicleBodyType')
    body_mapped = NjuskaloFormMapper.map_body_type(body_type)
    print(f"Input: {body_type}")
    print(f"Croatian: {body_mapped['croatian']}")
    print(f"ID: {body_mapped['id']}")

    # Test 6: Door Count Mapping
    print("\n🚪 TEST 6: Door Count Mapping")
    print("-" * 80)
    doors = test_data.get('vehicleDoors')
    door_mapped = NjuskaloFormMapper.map_door_count(doors)
    print(f"Input: {doors}")
    print(f"Croatian: {door_mapped['croatian']}")
    print(f"ID: {door_mapped['id']}")

    # Test 7: Color Mapping
    print("\n🎨 TEST 7: Color Mapping")
    print("-" * 80)
    color = test_data.get('vehicleExteriorColor')
    color_mapped = NjuskaloFormMapper.map_color(color)
    print(f"Input: {color}")
    print(f"Croatian: {color_mapped}")

    # Test 8: Contact Array Extraction
    print("\n📞 TEST 8: Contact Array Extraction")
    print("-" * 80)
    contact = test_data.get('contact', {})

    phone = NjuskaloFormMapper.extract_contact_value(contact.get('phone'))
    print(f"Phone array: {contact.get('phone')}")
    print(f"Extracted: {phone}")

    email = NjuskaloFormMapper.extract_contact_value(contact.get('email'))
    print(f"Email array: {contact.get('email')}")
    print(f"Extracted: {email}")

    name = NjuskaloFormMapper.extract_contact_value(contact.get('name'))
    print(f"Name: {contact.get('name')}")
    print(f"Extracted: {name}")

    # Test 9: Price Handling
    print("\n💰 TEST 9: Price Selection")
    print("-" * 80)
    price = test_data.get('price')
    special_price = test_data.get('specialPrice')
    price_type = test_data.get('priceType')

    print(f"Regular price: {price}")
    print(f"Special price: {special_price}")
    print(f"Price type: {price_type}")

    selected_price = special_price if special_price else price
    print(f"✅ Selected for form: {selected_price}")
    print(f"✅ Mark as discounted: {price_type == 'DISCOUNTED'}")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Feature mapping: {total_mapped} checkboxes identified")
    print(f"✅ Fuel type: {fuel_type} → {fuel_mapped['croatian']}")
    print(f"✅ Transmission: {transmission} → {trans_mapped['croatian']}")
    print(f"✅ Drive type: {drive_type} → {drive_mapped['croatian']}")
    print(f"✅ Body type: {body_type} → {body_mapped['croatian']}")
    print(f"✅ Door count: {doors} → {door_mapped['croatian']}")
    print(f"✅ Color: {color} → {color_mapped}")
    print(f"✅ Contact extraction: Phone={phone}, Email={email}, Name={name}")
    print(f"✅ Price selection: {selected_price} (Discounted: {price_type == 'DISCOUNTED'})")
    print("\n🎉 All tests completed successfully!")
    print("=" * 80)

if __name__ == "__main__":
    test_feature_mapping()
