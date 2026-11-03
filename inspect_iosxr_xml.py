import xml.etree.ElementTree as ET


XML_FILE = "iosxr_teacher_data.xml"


try:
    tree = ET.parse(XML_FILE)
    root = tree.getroot()

    print("=" * 60)
    print("IOS XR XML Structure")
    print("=" * 60)

    print("Root tag:")
    print(root.tag)

    print("\nTop-level XML sections:")

    for number, child in enumerate(root, start=1):
        print(f"{number}. {child.tag}")

    print("\nXML structure inspection completed.")

except FileNotFoundError:
    print("XML file was not found:", XML_FILE)

except ET.ParseError as error:
    print("XML parsing failed:")
    print(error)

except Exception as error:
    print("Unexpected error:")
    print(error)