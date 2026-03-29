from stix2validator import validate_string, ValidationOptions

BUNDLE_PATH = r'<test_bundle_path>'

with open(BUNDLE_PATH) as f:
    content = f.read()

# Run validation
# Set strict=True to treat warnings (best practices) as errors
results = validate_string(content, options=ValidationOptions(version="2.1"))

if results.is_valid:
    print("Bundle is valid!")
else:
    print("Bundle is invalid:")
    print(results.errors)

# Example 2: Validation Options (Allow custom objects)
# opts = ValidationOptions(allow_custom=True)
# results = validate_string(custom_stix_json, options=opts)
