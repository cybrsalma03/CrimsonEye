import re
import random

class NucleiHandler:
    def validate_template(self, template):
        """Validate a Nuclei template."""
        if "id" not in template:
            return False
        if "info" not in template:
            return False
        if "requests" not in template and "http" not in template:
            return False
        return True

    def generate_payload(self, payload):
        """Generate dynamic payloads for Nuclei templates."""
        if "{{randstr}}" in payload:
            payload = payload.replace("{{randstr}}", self._generate_random_string())
        if "{{randint}}" in payload:
            payload = payload.replace("{{randint}}", str(self._generate_random_int()))
        return payload

    def _generate_random_string(self, length: int = 10) -> str:
        """Generate a random string of a given length."""
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def _generate_random_int(self, min_val: int = 1, max_val: int = 1000) -> int:
        """Generate a random integer between min_val and max_val."""
        return random.randint(min_val, max_val)

    def match_response(self, response, matcher):
        """Check if the response matches the matcher criteria."""
        matcher_type = matcher.get("type")
        if matcher_type == "regex":
            return bool(re.search(matcher.get("regex", ""), response.text))
        elif matcher_type == "status":
            return response.status_code in matcher.get("status", [])
        elif matcher_type == "word":
            return any(word in response.text for word in matcher.get("words", []))
        return False

    def get_template_validation_errors(self, template):
        """Get validation errors for a template."""
        errors = []
        if "id" not in template:
            errors.append("Missing 'id' field")
        if "info" not in template:
            errors.append("Missing 'info' field")
        if "requests" not in template and "http" not in template:
            errors.append("Missing 'requests' or 'http' field")
        return errors

    def suggest_fix_for_template(self, errors):
        """Provide suggestions to fix invalid templates."""
        suggestions = []
        for error in errors:
            if "Missing 'id' field" in error:
                suggestions.append("Add a unique 'id' field to the template.")
            if "Missing 'info' field" in error:
                suggestions.append("Add an 'info' field with details like severity and tags.")
            if "Missing 'requests' or 'http' field" in error:
                suggestions.append("Add a 'requests' or 'http' field with at least one request.")
        return "; ".join(suggestions)