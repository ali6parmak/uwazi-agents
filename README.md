Tasks

[ ] Analyze data in Uwazi
    [ ] Trends
    [ ] Plot data
    [ ] Evolution of events in time in a map
    [ ] Timeline of entities from different templates
[ ] Use local models

[x] Use XML instead of dictionaries
[x] Query templates
[x] Query entities
[-] Create an entity
[-] Create templates
    [-] Using all property types
[x] Ask for validation
[ ] Create templates
    result = create_template(
        name="test_validation",
        properties=[
            {"label": "Valid Property", "type": "text", "required": True},
            {"label": "Invalid Type", "type": "invalid_type", "required": True},
            {"label": "Extra Fields", "type": "date", "invalid_field": "should be removed", "another_bad_field": 123},
            "not a dict",
            {"label": "Missing Type"},
            {"label": "Valid Markdown", "type": "markdown", "showInCard": True},
        ],
        color="#C03B22",
    )
    print(result)

Demo

Create templates for holding the data for the organization The Armed Conflict Location & Event Data Project
Create templates for holding the data for the organization UN Human Rights Treaty Bodies Jurisprudence