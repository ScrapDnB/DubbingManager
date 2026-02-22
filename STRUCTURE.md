dubbing_manager/
├── main.py
├── requirements.txt
├── README.md
├── config/
│   ├── __init__.py
│   └── constants.py
├── core/
│   ├── __init__.py
│   ├── project_data.py
│   ├── ass_parser.py
│   └── models.py
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── teleprompter.py
│   ├── preview.py
│   ├── video.py
│   └── dialogs/
│       ├── __init__.py
│       ├── actor_filter.py
│       ├── colors.py
│       ├── export.py
│       ├── hotkeys.py
│       ├── reaper.py
│       ├── roles.py
│       ├── search.py
│       └── summary.py
├── services/
│   ├── __init__.py
│   ├── osc_worker.py
│   └── hotkey_manager.py
└── utils/
    ├── __init__.py
    ├── helpers.py
    └── web_bridge.py