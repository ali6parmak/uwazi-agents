from smolagents import CodeAgent, LiteLLMModel, tool
from mock_uwazi import MockUwaziAdapter as UwaziAdapter
from config import url, user, password
import json


# ============================================================================
# HELPER TOOLS FOR AGENT CONTEXT
# ============================================================================

@tool
def analyze_existing_templates() -> str:
    """
    Analyzes all existing templates and provides a summary of their structure.
    
    This tool helps understand what templates already exist and their characteristics,
    which is useful before creating new templates to avoid duplication.
    
    Returns:
        A formatted text summary of all templates and their properties.
    """
    try:
        if not all([url, user, password]):
            return "Error: Missing Uwazi credentials"
        
        uwazi = UwaziAdapter(user=user, password=password, url=url)
        templates = uwazi.templates.get()
        
        if not templates:
            return "No templates found in the database."
        
        summary_parts = [f"Found {len(templates)} template(s):\n"]
        
        for template in templates:
            summary_parts.append(f"\n--- Template: {template.get('name', 'N/A')} (ID: {template.get('_id', 'N/A')}) ---")
            summary_parts.append(f"Color: {template.get('color', 'N/A')}")
            
            properties = template.get('properties', [])
            summary_parts.append(f"Number of custom properties: {len(properties)}")
            
            if properties:
                summary_parts.append("\nCustom Properties:")
                for prop in properties:
                    required_str = " (REQUIRED)" if prop.get('required') else ""
                    filter_str = " (FILTERABLE)" if prop.get('filter') else ""
                    summary_parts.append(
                        f"  - {prop.get('label', 'N/A')}: {prop.get('type', 'N/A')}{required_str}{filter_str}"
                    )
        
        return "\n".join(summary_parts)
    except Exception as e:
        return f"Error analyzing templates: {str(e)}"


@tool
def suggest_template_properties(domain: str) -> str:
    """
    Suggests property structures based on a given domain or use case.
    
    This tool provides intelligent suggestions for what properties a template
    should have based on the domain (e.g., "research paper", "event", "product").
    
    Args:
        domain: The domain or use case for the template (e.g., "research paper", "event", "recipe")
    
    Returns:
        JSON string with suggested properties that can be used with create_template.
    """
    domain_suggestions = {
        "research paper": [
            {"label": "Authors", "type": "text", "required": True, "showInCard": True},
            {"label": "Abstract", "type": "markdown", "required": True},
            {"label": "Publication Date", "type": "date", "filter": True},
            {"label": "Journal", "type": "text", "filter": True},
            {"label": "DOI", "type": "link"},
            {"label": "Keywords", "type": "multiselect", "filter": True},
            {"label": "PDF", "type": "media"},
        ],
        "event": [
            {"label": "Event Date", "type": "date", "required": True, "filter": True},
            {"label": "Location", "type": "geolocation", "required": True},
            {"label": "Description", "type": "markdown"},
            {"label": "Organizer", "type": "text", "showInCard": True},
            {"label": "Capacity", "type": "numeric"},
            {"label": "Registration Link", "type": "link"},
            {"label": "Event Image", "type": "image"},
        ],
        "recipe": [
            {"label": "Ingredients", "type": "markdown", "required": True},
            {"label": "Instructions", "type": "markdown", "required": True},
            {"label": "Prep Time (minutes)", "type": "numeric"},
            {"label": "Cook Time (minutes)", "type": "numeric"},
            {"label": "Servings", "type": "numeric"},
            {"label": "Difficulty", "type": "select", "filter": True},
            {"label": "Cuisine Type", "type": "select", "filter": True},
            {"label": "Recipe Image", "type": "image"},
        ],
        "contact": [
            {"label": "Full Name", "type": "text", "required": True, "showInCard": True},
            {"label": "Email", "type": "text", "required": True},
            {"label": "Phone", "type": "text"},
            {"label": "Company", "type": "text", "filter": True},
            {"label": "Position", "type": "text"},
            {"label": "Notes", "type": "markdown"},
            {"label": "Last Contact Date", "type": "date"},
        ],
        "project": [
            {"label": "Project Manager", "type": "text", "required": True, "showInCard": True},
            {"label": "Description", "type": "markdown"},
            {"label": "Start Date", "type": "date", "required": True, "filter": True},
            {"label": "End Date", "type": "date", "filter": True},
            {"label": "Status", "type": "select", "required": True, "filter": True},
            {"label": "Budget", "type": "numeric"},
            {"label": "Team Members", "type": "multiselect"},
        ],
        "product": [
            {"label": "Price", "type": "numeric", "required": True, "showInCard": True},
            {"label": "Description", "type": "markdown", "required": True},
            {"label": "Category", "type": "select", "filter": True},
            {"label": "SKU", "type": "text"},
            {"label": "Stock Quantity", "type": "numeric"},
            {"label": "Images", "type": "media"},
            {"label": "Specifications", "type": "markdown"},
        ],
        "blog post": [
            {"label": "Author", "type": "text", "required": True, "showInCard": True},
            {"label": "Content", "type": "markdown", "required": True},
            {"label": "Publish Date", "type": "date", "filter": True},
            {"label": "Tags", "type": "multiselect", "filter": True},
            {"label": "Featured Image", "type": "image"},
            {"label": "Excerpt", "type": "text"},
            {"label": "Status", "type": "select", "filter": True},
        ],
    }
    
    domain_lower = domain.lower()
    suggestions = None
    matched_domain = None
    
    # Find matching domain
    for key in domain_suggestions:
        if key in domain_lower or domain_lower in key:
            suggestions = domain_suggestions[key]
            matched_domain = key
            break
    
    if not suggestions:
        return json.dumps({
            "error": f"No specific suggestions for domain '{domain}'",
            "hint": "Consider using generic properties like: description (markdown), category (select), date (date), status (select)",
            "available_domains": list(domain_suggestions.keys())
        }, indent=2)
    
    result = {
        "domain": matched_domain,
        "suggested_properties": suggestions,
        "usage_hint": "Pass the 'suggested_properties' array directly to create_template's properties parameter"
    }
    
    return json.dumps(result, indent=2)


# ============
# CORE TOOLS
# ============

@tool
def get_all_templates(fields: str) -> str:
    """
    Retrieves all templates from Uwazi instance as XML with configurable field selection.

    This tool connects to a Uwazi instance and fetches all available templates.
    Templates define the structure of entities in Uwazi, containing properties
    that define the fields entities can have.

    AI agents can specify which fields to include in the XML output to reduce
    data size and processing time. Only the requested fields will be included
    in the response.

    Args:
        fields: Comma-separated list of fields to include in the XML output.
                Available fields: id, name, properties, commonProperties
                Example: "id,name,properties" to include template properties
                Use "all" to include all available fields

    Returns:
        XML formatted string containing templates with requested fields.
        Returns empty templates element on error or if no credentials.
    """
    try:
        if not all([url, user, password]):
            return '<?xml version="1.0" encoding="UTF-8"?><templates><error>Missing credentials</error></templates>'

        uwazi = UwaziAdapter(user=user, password=password, url=url)
        templates_raw = uwazi.templates.get()

        requested_fields = (
            [f.strip() for f in fields.split(",")] if fields != "all" else ["id", "name", "properties", "commonProperties"]
        )

        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<templates>"]

        for template in templates_raw:
            xml_parts.append("  <template>")

            if "id" in requested_fields:
                xml_parts.append(f'    <id>{template.get("_id", "")}</id>')

            if "name" in requested_fields:
                xml_parts.append(f'    <name>{template.get("name", "")}</name>')

            if "properties" in requested_fields:
                xml_parts.append("    <properties>")
                for prop in template.get("properties", []):
                    xml_parts.append("      <property>")
                    xml_parts.append(f'        <name>{prop.get("name", "")}</name>')
                    xml_parts.append(f'        <type>{prop.get("type", "")}</type>')
                    if prop.get("label"):
                        xml_parts.append(f'        <label>{prop.get("label", "")}</label>')
                    if prop.get("required"):
                        xml_parts.append(f'        <required>{prop.get("required", False)}</required>')
                    if prop.get("filter"):
                        xml_parts.append(f'        <filter>{prop.get("filter", False)}</filter>')
                    xml_parts.append("      </property>")
                xml_parts.append("    </properties>")

            if "commonProperties" in requested_fields:
                xml_parts.append("    <commonProperties>")
                for prop in template.get("commonProperties", []):
                    xml_parts.append("      <property>")
                    xml_parts.append(f'        <name>{prop.get("name", "")}</name>')
                    xml_parts.append(f'        <type>{prop.get("type", "")}</type>')
                    if prop.get("label"):
                        xml_parts.append(f'        <label>{prop.get("label", "")}</label>')
                    xml_parts.append("      </property>")
                xml_parts.append("    </commonProperties>")

            xml_parts.append("  </template>")

        xml_parts.append("</templates>")
        return "\n".join(xml_parts)
    except Exception as e:
        return f'<?xml version="1.0" encoding="UTF-8"?><templates><error>{str(e)}</error></templates>'


@tool
def get_all_entities(template_id: str, fields: str, batch_size: int = 30, language: str = "en") -> str:
    """
    Retrieves all entities for a given template from Uwazi instance as XML with configurable field selection.

    This tool connects to a Uwazi instance and fetches all entities for a specified template.
    It handles pagination automatically, retrieving entities in batches until all entities
    are collected.

    AI agents can specify which fields to include in the XML output to reduce
    data size and processing time. Only the requested fields will be included
    in the response.

    Args:
        template_id: The id of the template for which to retrieve entities.
        fields: Comma-separated list of fields to include in the XML output.
                Available fields: id, sharedId, title, template, metadata
                Example: "id,title" for minimal output
                Use "all" to include all available fields
        batch_size: The number of entities to retrieve per batch (default: 30).
        language: The language in which to retrieve the entities (default: "en").

    Returns:
        XML formatted string containing entities with requested fields.
        Returns empty entities element on error or if no credentials.
    """
    try:
        if not all([url, user, password]):
            return '<?xml version="1.0" encoding="UTF-8"?><entities><error>Missing credentials</error></entities>'

        uwazi = UwaziAdapter(user=user, password=password, url=url)
        entities = []
        start_from = 0
        while True:
            batch = uwazi.entities.get(
                start_from=start_from, batch_size=batch_size, template_id=template_id, language=language
            )
            if not batch:
                break
            entities.extend(batch)
            if len(batch) < batch_size:
                break
            start_from += batch_size

        requested_fields = (
            [f.strip() for f in fields.split(",")]
            if fields != "all"
            else ["id", "sharedId", "title", "template", "metadata"]
        )

        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', f'<entities count="{len(entities)}">']

        for entity in entities:
            xml_parts.append("  <entity>")

            if "id" in requested_fields and "_id" in entity:
                xml_parts.append(f'    <id>{entity.get("_id", "")}</id>')

            if "sharedId" in requested_fields and "sharedId" in entity:
                xml_parts.append(f'    <sharedId>{entity.get("sharedId", "")}</sharedId>')

            if "title" in requested_fields and "title" in entity:
                xml_parts.append(f'    <title>{entity.get("title", "")}</title>')

            if "template" in requested_fields and "template" in entity:
                xml_parts.append(f'    <template>{entity.get("template", "")}</template>')

            if "metadata" in requested_fields and "metadata" in entity:
                metadata = entity.get("metadata", {})
                if metadata:
                    xml_parts.append("    <metadata>")
                    for key, value in metadata.items():
                        # Handle lists/arrays in metadata
                        if isinstance(value, list):
                            xml_parts.append(f"      <{key}>")
                            for item in value:
                                xml_parts.append(f"        <item>{item}</item>")
                            xml_parts.append(f"      </{key}>")
                        else:
                            xml_parts.append(f"      <{key}>{value}</{key}>")
                    xml_parts.append("    </metadata>")

            xml_parts.append("  </entity>")

        xml_parts.append("</entities>")
        return "\n".join(xml_parts)
    except Exception as e:
        return f'<?xml version="1.0" encoding="UTF-8"?><entities><error>{str(e)}</error></entities>'


@tool
def create_template(name: str, properties: list[dict], color: str = "#000000", language: str = "en") -> str:
    """
    Creates a new template in the Uwazi instance.

    This tool creates a new template that defines the structure for entities in Uwazi.
    Templates contain properties that define what fields entities will have.

    AI agents should call this function with a template name and a list of property dictionaries.
    Each property is a simple dictionary with keys like label, type, required, etc.

    Args:
        name: The name of the template to create
        properties: List of property dictionaries. Each property dict can have:
            - label (str, required): Display name for the property. 
              Avoid labels like "Title", "Date added", "Date modified" as they are already created by default
            - type (str, required): Property type - one of: text, markdown, numeric, date,
                                   link, select, multiselect, relationship, nested, image,
                                   media, preview, geolocation
            - required (bool, optional): If True, field is mandatory. Default: False
            - showInCard (bool, optional): Show in entity card preview. Default: False
            - filter (bool, optional): Can be used to filter entities. Default: False
            - defaultfilter (bool, optional): Show as default filter in UI. Default: False
            - prioritySorting (bool, optional): Prioritize in sorting. Default: False
            - noLabel (bool, optional): Hide label in UI. Default: False
            - style (str, optional): CSS style string. Default: ""
        color: Hex color code for the template. Default: "#000000"
        language: Language code for the template. Default: "en"

    Returns:
        JSON string with the created template including its generated ID, or error message

    Example usage for AI agents:
        create_template(
            name="Person",
            properties=[
                {"label": "Full Name", "type": "text", "required": True, "showInCard": True},
                {"label": "Biography", "type": "markdown"},
                {"label": "Birth Date", "type": "date", "filter": True}
            ],
            color="#4A90E2"
        )
    """
    try:
        if not all([url, user, password]):
            return json.dumps({"error": "Missing required environment variables (UWAZI_URL, UWAZI_USER, UWAZI_PASSWORD)"})

        uwazi = UwaziAdapter(user=user, password=password, url=url)

        valid_property_fields = {
            "label", "type", "name", "required", "showInCard", "filter",
            "defaultfilter", "prioritySorting", "noLabel", "style",
            "generatedId", "isCommonProperty",
        }

        valid_property_types = {
            "text", "markdown", "numeric", "date", "link", "select",
            "multiselect", "relationship", "nested", "image", "media",
            "preview", "geolocation",
        }

        cleaned_properties = []
        validation_warnings = []
        
        for idx, prop in enumerate(properties):
            if not isinstance(prop, dict):
                validation_warnings.append(f"Property at index {idx} is not a dictionary, skipping")
                continue

            if "type" not in prop:
                validation_warnings.append(f"Property at index {idx} missing 'type' field, skipping")
                continue

            if prop["type"] not in valid_property_types:
                validation_warnings.append(f"Property at index {idx} has invalid type '{prop['type']}', skipping")
                continue

            cleaned_prop = {key: value for key, value in prop.items() if key in valid_property_fields}

            if "label" not in cleaned_prop:
                cleaned_prop["label"] = ""
                validation_warnings.append(f"Property at index {idx} missing 'label', using empty string")

            # Auto-generate name from label if not provided
            if "name" not in cleaned_prop and cleaned_prop.get("label"):
                cleaned_prop["name"] = cleaned_prop["label"].lower().replace(" ", "_")

            cleaned_properties.append(cleaned_prop)

        template_dict = {
            "name": name,
            "color": color,
            "entityViewPage": "",
            "properties": cleaned_properties,
            "commonProperties": [
                {"label": "Title", "name": "title", "type": "text", "isCommonProperty": True},
                {"label": "Date added", "name": "creationDate", "type": "date", "isCommonProperty": True},
                {"label": "Date modified", "name": "editDate", "type": "date", "isCommonProperty": True},
            ],
        }

        result = uwazi.templates.set(language=language, template=template_dict)
        
        # Add validation warnings to result
        if validation_warnings:
            result["validation_warnings"] = validation_warnings
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Error creating template: {str(e)}"})


# ============================================================================
# AGENT SETUP EXAMPLE
# ============================================================================

def create_uwazi_agent(model):
    """
    Creates an agent that can intelligently manage Uwazi templates.
    
    The agent can:
    - Analyze existing templates
    - Get suggestions for new templates based on domain
    - Create new templates with proper validation
    - Query entities and templates
    
    Args:
        model: LiteLLMModel or other smolagents-compatible model
    
    Returns:
        Configured CodeAgent instance
    """
    from smolagents import CodeAgent
    
    agent = CodeAgent(
        tools=[
            analyze_existing_templates,
            suggest_template_properties,
            get_all_templates,
            get_all_entities,
            create_template,
        ],
        model=model,
        additional_authorized_imports=["json"]
    )
    
    return agent


def main():
    """
    Demonstrates various ways to use the Uwazi agent.
    """
    
    # ========================================================================
    # SETUP: Create the agent
    # ========================================================================
    
    model = LiteLLMModel(
        model_id="ollama/qwen2.5-coder:14b",  # or any other model
        # api_base="http://localhost:11434",  # if using local Ollama
    )
    
    agent = CodeAgent(
        tools=[
            analyze_existing_templates,
            suggest_template_properties,
            get_all_templates,
            get_all_entities,
            create_template,
        ],
        model=model,
        additional_authorized_imports=["json"],
        max_steps=10,  # Limit steps to prevent infinite loops
    )
    
    print("🤖 Uwazi Agent initialized!\n")
    
    # ========================================================================
    # EXAMPLE 1: Simple analysis
    # ========================================================================
    
    print("=" * 80)
    print("EXAMPLE 1: Analyze existing templates")
    print("=" * 80)
    
    result = agent.run(
        "What templates currently exist in the Uwazi system? Give me a detailed summary."
    )
    print(result)
    print("\n")
    
    # ========================================================================
    # EXAMPLE 2: Create template with domain suggestions
    # ========================================================================
    
    print("=" * 80)
    print("EXAMPLE 2: Create a research paper template")
    print("=" * 80)
    
    result = agent.run(
        """I need to create a template for managing research papers in our academic database.
        
        Please:
        1. First check if a similar template already exists
        2. If not, get suggestions for appropriate properties for research papers
        3. Create the template with a professional blue color (#2563EB)
        4. Make sure important fields like authors and abstract are required
        """
    )
    print(result)
    print("\n")
    
    # ========================================================================
    # EXAMPLE 3: Create custom template from scratch
    # ========================================================================
    
    print("=" * 80)
    print("EXAMPLE 3: Create a custom Job Application template")
    print("=" * 80)
    
    result = agent.run(
        """Create a template called 'Job Application' for tracking job applications.
        
        It should include:
        - Company name (required, show in card)
        - Position title (required, show in card)
        - Application date (required, filterable)
        - Status (select field, required, filterable) - options like: Applied, Interview, Offer, Rejected
        - Salary range (numeric)
        - Contact person name
        - Contact email
        - Notes (markdown for detailed notes)
        - Follow-up date
        
        Use a professional green color like #059669.
        """
    )
    print(result)
    print("\n")
    
    # ========================================================================
    # EXAMPLE 4: Query entities from a template
    # ========================================================================
    
    print("=" * 80)
    print("EXAMPLE 4: Query entities")
    print("=" * 80)
    
    result = agent.run(
        """Show me all entities from the 'Blog Post' template.
        I want to see their titles and metadata.
        """
    )
    print(result)
    print("\n")
    
    # ========================================================================
    # EXAMPLE 5: Complex multi-step workflow
    # ========================================================================
    
    print("=" * 80)
    print("EXAMPLE 5: Complex workflow - Recipe management system")
    print("=" * 80)
    
    result = agent.run(
        """I'm building a recipe management system for a cooking blog.
        
        Please help me set this up:
        1. First, analyze what templates currently exist to avoid duplicates
        2. Check if there's already a recipe-related template
        3. If not, get suggestions for recipe template properties
        4. Create a comprehensive recipe template with:
           - All the suggested properties
           - Make ingredients and instructions required
           - Make cooking time, difficulty, and cuisine type filterable
           - Include fields for images
        5. Use a warm, food-related color like #F59E0B (orange)
        
        After creating it, confirm the template was created successfully.
        """
    )
    print(result)
    print("\n")
    
    # ========================================================================
    # EXAMPLE 6: Interactive mode
    # ========================================================================
    
    print("=" * 80)
    print("EXAMPLE 6: Interactive mode")
    print("=" * 80)
    print("You can now chat with the agent interactively!")
    print("Type 'quit' or 'exit' to stop.\n")
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        if not user_input:
            continue
        
        try:
            result = agent.run(user_input)
            print(f"\n🤖 Agent: {result}\n")
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


# ============================================================================
# ALTERNATIVE: Simpler single-task examples
# ============================================================================

def quick_examples():
    """Quick one-liner examples for common tasks"""
    
    model = LiteLLMModel(model_id="ollama/qwen2.5-coder:14b")
    agent = CodeAgent(
        tools=[
            analyze_existing_templates,
            suggest_template_properties,
            get_all_templates,
            get_all_entities,
            create_template,
        ],
        model=model,
        additional_authorized_imports=["json"],
    )
    
    # Quick task 1: Just analyze
    print("📊 Quick Analysis:")
    print(agent.run("What templates exist?"))
    print("\n")
    
    # Quick task 2: Get suggestions
    print("💡 Get Suggestions:")
    print(agent.run("What properties should a contact management template have?"))
    print("\n")
    
    # Quick task 3: Create simple template
    print("✨ Create Simple Template:")
    print(agent.run(
        "Create a 'Book' template with title, author, ISBN, publication date, and description. "
        "Use color #8B5CF6."
    ))
    print("\n")


# ============================================================================
# ADVANCED: Error handling and retries
# ============================================================================

def robust_agent_run(agent, task, max_retries=3):
    """
    Run agent with error handling and retries.
    
    Args:
        agent: The CodeAgent instance
        task: The task string to execute
        max_retries: Maximum number of retry attempts
    
    Returns:
        Result string or error message
    """
    for attempt in range(max_retries):
        try:
            print(f"🔄 Attempt {attempt + 1}/{max_retries}")
            result = agent.run(task)
            print("✅ Success!")
            return result
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                print("Retrying...\n")
            else:
                print("Max retries reached.")
                return f"Error after {max_retries} attempts: {str(e)}"


def advanced_example():
    """Example with error handling"""
    
    model = LiteLLMModel(model_id="ollama/qwen2.5-coder:14b")
    agent = CodeAgent(
        tools=[
            analyze_existing_templates,
            suggest_template_properties,
            get_all_templates,
            get_all_entities,
            create_template,
        ],
        model=model,
        additional_authorized_imports=["json"],
    )
    
    task = """
    Create an 'Event' template for managing conferences and workshops.
    Include event date, location, organizer, capacity, and registration link.
    Use color #DC2626.
    """
    
    result = robust_agent_run(agent, task, max_retries=3)
    print(f"\nFinal Result:\n{result}")


# ============================================================================
# BATCH PROCESSING: Multiple templates at once
# ============================================================================

def batch_create_templates():
    """Create multiple templates in one session"""
    
    model = LiteLLMModel(model_id="ollama/qwen2.5-coder:14b")
    agent = CodeAgent(
        tools=[
            analyze_existing_templates,
            suggest_template_properties,
            get_all_templates,
            get_all_entities,
            create_template,
        ],
        model=model,
        additional_authorized_imports=["json"],
    )
    
    templates_to_create = [
        {
            "name": "Event",
            "description": "conferences and workshops with date, location, organizer",
            "color": "#DC2626"
        },
        {
            "name": "Product",
            "description": "e-commerce products with price, description, category",
            "color": "#059669"
        },
        {
            "name": "Contact",
            "description": "business contacts with name, email, company, position",
            "color": "#2563EB"
        },
    ]
    
    print("🚀 Batch creating templates...\n")
    
    for template_spec in templates_to_create:
        print(f"Creating: {template_spec['name']}")
        print("-" * 40)
        
        task = f"""
        Create a '{template_spec['name']}' template for {template_spec['description']}.
        First check if it already exists. If not, get domain suggestions and create it.
        Use color {template_spec['color']}.
        """
        
        try:
            result = agent.run(task)
            print(f"✅ {template_spec['name']} created successfully")
            print(f"Result: {result[:200]}...\n")  # Print first 200 chars
        except Exception as e:
            print(f"❌ Failed to create {template_spec['name']}: {str(e)}\n")


# ============================================================================
# CONVERSATIONAL: Multi-turn conversation
# ============================================================================

def conversational_example():
    """Example showing multi-turn conversation with context"""
    
    model = LiteLLMModel(model_id="ollama/qwen2.5-coder:14b")
    agent = CodeAgent(
        tools=[
            analyze_existing_templates,
            suggest_template_properties,
            get_all_templates,
            get_all_entities,
            create_template,
        ],
        model=model,
        additional_authorized_imports=["json"],
    )
    
    conversation = [
        "What templates currently exist in the system?",
        "I want to create a template for managing research papers. What properties should it have?",
        "Great! Now create that research paper template with those properties. Use a blue color.",
        "Can you show me the details of the template we just created?",
    ]
    
    print("💬 Conversational Example\n")
    
    for i, message in enumerate(conversation, 1):
        print(f"\n{'='*80}")
        print(f"Turn {i}")
        print(f"{'='*80}")
        print(f"User: {message}")
        print("\nAgent: ", end="")
        
        try:
            result = agent.run(message)
            print(result)
        except Exception as e:
            print(f"Error: {str(e)}")


# ============================================================================
# RUN EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║           Uwazi Template Management Agent Examples             ║
    ╚════════════════════════════════════════════════════════════════╝
    
    Choose an example to run:
    
    1. Full demo with all examples
    2. Quick examples (fast)
    3. Advanced example with error handling
    4. Batch create multiple templates
    5. Conversational multi-turn example
    6. Interactive mode (chat with agent)
    
    """)
    
    choice = input("Enter choice (1-6): ").strip()
    
    if choice == "1":
        main()
    elif choice == "2":
        quick_examples()
    elif choice == "3":
        advanced_example()
    elif choice == "4":
        batch_create_templates()
    elif choice == "5":
        conversational_example()
    elif choice == "6":
        # Just run interactive mode
        model = LiteLLMModel(model_id="ollama/qwen2.5-coder:14b")
        agent = CodeAgent(
            tools=[
                analyze_existing_templates,
                suggest_template_properties,
                get_all_templates,
                get_all_entities,
                create_template,
            ],
            model=model,
            additional_authorized_imports=["json"],
        )
        
        print("\n💬 Interactive Mode - Chat with the agent!")
        print("Type 'quit' to exit.\n")
        
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            if user_input:
                try:
                    result = agent.run(user_input)
                    print(f"\n🤖 Agent: {result}\n")
                except Exception as e:
                    print(f"\n❌ Error: {str(e)}\n")
    else:
        print("Invalid choice. Running full demo...")
        main()