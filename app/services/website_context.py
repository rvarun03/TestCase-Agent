def prepare_page_context(page_data:dict) ->dict:

    # STEP 1: Basic page information
    context = {
        "url": page_data["url"],
        "title": page_data["title"],
        "content": [],
        "buttons": [],
        "links": [],
        "forms": []
    }

    # STEP 2: Extract meaningful content
    for block in page_data.get("content_blocks", []):

        context["content"].append({
            "type": block["type"],
            "text": block["text"]
        })

    # STEP 3: Extract buttons
    for button in page_data.get("buttons", []):

        context["buttons"].append({
            "text": button["text"],
            "category": button["semantic_category"],
            "disabled": button["disabled"]
        })

    # STEP 4: Extract links
    for link in page_data.get("links", []):

        if not link.get("text"):
            continue

        context["links"].append({
            "text": link["text"],
            "href": link["href"],
            "category": link["semantic_category"],
            "scope": link["scope"]
        })

    # STEP 5: Extract forms
    for form in page_data.get("forms", []):

        fields = []

        for field in form.get("fields", []):

            fields.append({
                "label": field.get("label"),
                "type": field.get("type"),
                "html_required": field.get("html_required"),
                "visually_marked_required": field.get(
                    "visually_marked_required"
                ),
                "options": field.get("options", []),
                "file_restrictions": field.get(
                    "file_restrictions"
                )
            })

        context["forms"].append({
            "form_id": form["form_id"],
            "fields": fields
        })

    return context