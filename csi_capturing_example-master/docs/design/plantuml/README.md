# PlantUML Design Package

This folder contains architecture/design diagrams for the unified CSI/RSSI experiment system.

Files:

- `01_system_context.puml` / `01_system_context.png`
- `02_component_architecture.puml` / `02_component_architecture.png`
- `03_capture_sequence.puml` / `03_capture_sequence.png`
- `04_data_model.puml` / `04_data_model.png`
- `05_validation_workflow.puml` / `05_validation_workflow.png`

Regenerate PNG files:

```bash
./scripts/generate_plantuml_pngs.sh
```

The script uses the Kroki PlantUML HTTP renderer and writes `.png` next to each `.puml`.
