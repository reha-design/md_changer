# Mermaid PDF Sample

This document combines a flowchart and a sequence diagram with ordinary Markdown.

## Conversion flow

```mermaid
flowchart LR
    A[Markdown source] --> B{Valid document?}
    B -->|Yes| C[Render diagrams]
    C --> D[Write PDF]
    B -->|No| E[Report error]
```

## Batch sequence

```mermaid
sequenceDiagram
    participant User
    participant Converter
    participant Chromium
    User->>Converter: Convert Markdown
    Converter->>Chromium: Load local HTML and Mermaid
    Chromium-->>Converter: Diagrams ready
    Converter-->>User: PDF and detailed result
```

| Feature | Expected result |
| --- | --- |
| Theme | Modern blue headings and diagram colors |
| Network | Offline rendering with bundled Mermaid |

```python
print("Ordinary code stays code")
```
