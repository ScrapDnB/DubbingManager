"""Native macOS window chrome for the QML application."""

from __future__ import annotations

import logging
import sys
from ctypes import c_void_p
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


logger = logging.getLogger(__name__)


if sys.platform == "darwin":
    import objc
    from AppKit import (
        NSApplication,
        NSBackingStoreBuffered,
        NSColor,
        NSFloatingWindowLevel,
        NSImage,
        NSMakeRect,
        NSMenu,
        NSMenuItem,
        NSPanel,
        NSPopUpButton,
        NSScreen,
        NSTextField,
        NSToolbar,
        NSToolbarDisplayModeIconOnly,
        NSToolbarFlexibleSpaceItemIdentifier,
        NSToolbarItem,
        NSToolbarSizeModeRegular,
        NSToolbarSpaceItemIdentifier,
        NSTitlebarSeparatorStyleNone,
        NSViewHeightSizable,
        NSViewWidthSizable,
        NSVisualEffectBlendingModeBehindWindow,
        NSVisualEffectBlendingModeWithinWindow,
        NSVisualEffectMaterialToolTip,
        NSVisualEffectMaterialWindowBackground,
        NSVisualEffectStateFollowsWindowActiveState,
        NSVisualEffectStateActive,
        NSVisualEffectView,
        NSWindowStyleMaskBorderless,
        NSWindowStyleMaskNonactivatingPanel,
        NSWindowToolbarStyleUnified,
    )
    from Foundation import NSClassFromString, NSObject


    class _ToolbarDelegate(NSObject):
        """AppKit delegate and action target retained by MacOSIntegration."""

        def initWithOwner_project_(self, owner, project):
            self = objc.super(_ToolbarDelegate, self).init()
            if self is None:
                return None
            self.owner = owner
            self.project = project
            self.items: dict[str, Any] = {}
            self.recent_paths: list[str] = []
            return self

        def toolbarAllowedItemIdentifiers_(self, _toolbar):
            return self.owner.toolbar_identifiers

        def toolbarDefaultItemIdentifiers_(self, _toolbar):
            return self.owner.default_toolbar_identifiers

        def toolbarSelectableItemIdentifiers_(self, _toolbar):
            return []

        def toolbar_itemForItemIdentifier_willBeInsertedIntoToolbar_(
            self, _toolbar, identifier, _will_insert
        ):
            key = str(identifier)
            if key == self.owner.RECENT:
                item = self._make_recent_item(identifier)
            else:
                item = self._make_action_item(identifier, key)
            self.items[key] = item
            return item

        def _make_action_item(self, identifier, key):
            definition = self.owner.ACTIONS[key]
            item = NSToolbarItem.alloc().initWithItemIdentifier_(identifier)
            item.setLabel_(definition[0])
            item.setPaletteLabel_(definition[0])
            item.setToolTip_(definition[0])
            image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                definition[1], definition[0]
            )
            if image is not None:
                item.setImage_(image)
            item.setTarget_(self)
            item.setAction_("toolbarAction:")
            return item

        def _make_recent_item(self, identifier):
            item = NSToolbarItem.alloc().initWithItemIdentifier_(identifier)
            item.setLabel_("Недавние проекты")
            item.setPaletteLabel_("Недавние проекты")
            popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
                NSMakeRect(0, 0, 210, 28), False
            )
            popup.setTarget_(self)
            popup.setAction_("recentProjectSelected:")
            item.setView_(popup)
            self.recent_popup = popup
            self.refresh_recent_projects()
            return item

        def toolbarAction_(self, sender):
            key = str(sender.itemIdentifier())
            callback = self.owner.ACTIONS.get(key, ("", "", None))[2]
            if callback:
                callback(self.owner, self.project)

        def recentProjectSelected_(self, sender):
            index = int(sender.indexOfSelectedItem()) - 1
            if 0 <= index < len(self.recent_paths):
                self.project.openRecent(self.recent_paths[index])
            sender.selectItemAtIndex_(0)

        def openSettings_(self, _sender):
            self.owner.globalSettingsRequested.emit()

        def openAbout_(self, _sender):
            self.owner.aboutRequested.emit()

        def validateToolbarItem_(self, item):
            key = str(item.itemIdentifier())
            if key == self.owner.SAVE:
                return bool(self.project.path)
            if key == self.owner.UNDO:
                return bool(self.project.canUndo)
            if key == self.owner.REDO:
                return bool(self.project.canRedo)
            return True

        def refresh_recent_projects(self):
            popup = getattr(self, "recent_popup", None)
            if popup is None:
                return
            popup.removeAllItems()
            popup.addItemWithTitle_("Недавние проекты")
            self.recent_paths = []
            model = self.project.recentProjectsModel
            roles = {
                bytes(name).decode("utf-8"): role
                for role, name in model.roleNames().items()
            }
            for row in range(model.rowCount()):
                index = model.index(row, 0)
                path = str(model.data(index, roles.get("path")) or "")
                name = str(model.data(index, roles.get("name")) or "")
                if not path:
                    continue
                popup.addItemWithTitle_(name or Path(path).name)
                self.recent_paths.append(path)


    class _ComboMenuTarget(NSObject):
        """Action target shared by native combo-box menus."""

        def initWithOwner_(self, owner):
            self = objc.super(_ComboMenuTarget, self).init()
            if self is not None:
                self.owner = owner
            return self

        def comboItemSelected_(self, sender):
            token = str(sender.representedObject() or "")
            self.owner.comboMenuSelected.emit(token, int(sender.tag()))


class MacOSIntegration(QObject):
    """Expose optional AppKit chrome without leaking it into shared QML."""

    nativeToolbarActiveChanged = Signal()
    openProjectRequested = Signal()
    saveProjectAsRequested = Signal()
    globalSettingsRequested = Signal()
    projectSettingsRequested = Signal()
    healthRequested = Signal()
    aboutRequested = Signal()
    comboMenuSelected = Signal(str, int)

    RECENT = "dm.recent"
    NEW = "dm.new"
    OPEN = "dm.open"
    SAVE = "dm.save"
    SAVE_AS = "dm.save-as"
    SETTINGS = "dm.settings"
    PROJECT_SETTINGS = "dm.project-settings"
    UNDO = "dm.undo"
    REDO = "dm.redo"
    HEALTH = "dm.health"
    ABOUT = "dm.about"

    ACTIONS: dict[str, tuple[str, str, Optional[Callable]]] = {
        NEW: ("Новый проект", "doc.badge.plus", lambda _o, p: p.create()),
        OPEN: ("Открыть проект", "folder", lambda o, _p: o.openProjectRequested.emit()),
        SAVE: ("Сохранить проект", "square.and.arrow.down", lambda _o, p: p.save()),
        SAVE_AS: (
            "Сохранить проект как",
            "square.and.arrow.down.on.square",
            lambda o, _p: o.saveProjectAsRequested.emit(),
        ),
        SETTINGS: (
            "Настройки программы",
            "gearshape",
            lambda o, _p: o.globalSettingsRequested.emit(),
        ),
        PROJECT_SETTINGS: (
            "Настройки проекта",
            "folder.badge.gearshape",
            lambda o, _p: o.projectSettingsRequested.emit(),
        ),
        UNDO: ("Отменить", "arrow.uturn.backward", lambda _o, p: p.undo()),
        REDO: ("Повторить", "arrow.uturn.forward", lambda _o, p: p.redo()),
        HEALTH: (
            "Проект: файлы и проверка",
            "checklist",
            lambda o, _p: o.healthRequested.emit(),
        ),
        ABOUT: (
            "О программе",
            "info.circle",
            lambda o, _p: o.aboutRequested.emit(),
        ),
    }

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._native_toolbar_active = False
        self._toolbar = None
        self._delegate = None
        self._ns_window = None
        self._effect_views: dict[int, Any] = {}
        self._tooltip_panel = None
        self._tooltip_label = None
        self._tooltip_effect = None
        self._combo_menu_target = None
        self._combo_token = 0

    @Property(bool, constant=True)
    def available(self) -> bool:
        return sys.platform == "darwin"

    @Property(bool, constant=True)
    def liquidGlassAvailable(self) -> bool:
        return (
            sys.platform == "darwin"
            and NSClassFromString("NSGlassEffectView") is not None
        )

    @Property(bool, notify=nativeToolbarActiveChanged)
    def nativeToolbarActive(self) -> bool:
        return self._native_toolbar_active

    @property
    def toolbar_identifiers(self) -> list[str]:
        if sys.platform != "darwin":
            return list(self.ACTIONS)
        return [
            self.RECENT,
            self.NEW,
            self.OPEN,
            self.SAVE,
            self.SAVE_AS,
            self.SETTINGS,
            self.PROJECT_SETTINGS,
            self.UNDO,
            self.REDO,
            self.HEALTH,
            self.ABOUT,
            NSToolbarFlexibleSpaceItemIdentifier,
            NSToolbarSpaceItemIdentifier,
        ]

    @property
    def default_toolbar_identifiers(self) -> list[str]:
        if sys.platform != "darwin":
            return list(self.ACTIONS)
        return [
            self.RECENT,
            NSToolbarSpaceItemIdentifier,
            self.NEW,
            self.OPEN,
            self.SAVE,
            self.SAVE_AS,
            NSToolbarSpaceItemIdentifier,
            self.SETTINGS,
            self.PROJECT_SETTINGS,
            NSToolbarFlexibleSpaceItemIdentifier,
            self.UNDO,
            self.REDO,
            NSToolbarSpaceItemIdentifier,
            self.HEALTH,
            self.ABOUT,
        ]

    def configure_main_window(self, window: QObject, project: QObject) -> None:
        if sys.platform != "darwin" or self._native_toolbar_active:
            return
        try:
            native_view = objc.objc_object(c_void_p=int(window.winId()))
            ns_window = native_view.window()
            self._install_visual_effect(native_view, ns_window)
            toolbar = NSToolbar.alloc().initWithIdentifier_(
                "com.yuriromanov.dubbingmanager.main-toolbar"
            )
            delegate = _ToolbarDelegate.alloc().initWithOwner_project_(
                self, project
            )
            toolbar.setDelegate_(delegate)
            toolbar.setDisplayMode_(NSToolbarDisplayModeIconOnly)
            toolbar.setSizeMode_(NSToolbarSizeModeRegular)
            toolbar.setAllowsUserCustomization_(True)
            toolbar.setAutosavesConfiguration_(True)
            ns_window.setToolbar_(toolbar)
            ns_window.setToolbarStyle_(NSWindowToolbarStyleUnified)
            ns_window.setTitlebarAppearsTransparent_(True)
            ns_window.setTitlebarSeparatorStyle_(NSTitlebarSeparatorStyleNone)
            ns_window.setBackgroundColor_(NSColor.windowBackgroundColor())
            self._configure_application_menu(delegate)
            QTimer.singleShot(
                0, lambda: self._configure_application_menu(delegate)
            )
            QTimer.singleShot(
                250, lambda: self._configure_application_menu(delegate)
            )

            project.recentProjectsChanged.connect(self.refresh_recent_projects)
            project.pathChanged.connect(self._validate_toolbar)
            project.undoStateChanged.connect(self._validate_toolbar)
            self._ns_window = ns_window
            self._toolbar = toolbar
            self._delegate = delegate
            self._native_toolbar_active = True
            self.nativeToolbarActiveChanged.emit()
        except Exception:
            logger.exception("Could not configure native macOS toolbar")

    def configure_window(self, window: Optional[QObject]) -> None:
        """Give every QML window a native macOS material substrate."""
        if sys.platform != "darwin" or window is None:
            return
        try:
            native_view = objc.objc_object(c_void_p=int(window.winId()))
            ns_window = native_view.window()
            if ns_window is not None:
                ns_window.setTitlebarAppearsTransparent_(True)
                ns_window.setTitlebarSeparatorStyle_(NSTitlebarSeparatorStyleNone)
                ns_window.setBackgroundColor_(NSColor.windowBackgroundColor())
                self._install_visual_effect(native_view, ns_window)
        except Exception:
            logger.debug(
                "Could not configure macOS material for an auxiliary window",
                exc_info=True,
            )

    def _install_visual_effect(self, native_view: Any, ns_window: Any) -> None:
        key = int(ns_window.windowNumber())
        if key in self._effect_views:
            return

        container = native_view.superview()
        if container is None:
            return

        effect = NSVisualEffectView.alloc().initWithFrame_(native_view.frame())
        effect.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        effect.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        effect.setMaterial_(NSVisualEffectMaterialWindowBackground)
        effect.setState_(NSVisualEffectStateFollowsWindowActiveState)
        container.addSubview_positioned_relativeTo_(effect, -1, native_view)
        self._effect_views[key] = effect

    @Slot(str, float, float)
    def showToolTip(self, text: str, x: float, y: float) -> None:
        """Show a non-activating native AppKit help tag."""
        if sys.platform != "darwin" or not text:
            return
        try:
            self._ensure_tooltip_panel()
            label = self._tooltip_label
            panel = self._tooltip_panel
            effect = self._tooltip_effect
            label.setStringValue_(text)
            label.sizeToFit()
            intrinsic = label.intrinsicContentSize()
            screen = NSScreen.mainScreen()
            screen_frame = screen.frame()
            visible_frame = screen.visibleFrame()
            max_width = max(34.0, float(visible_frame.size.width) - 8.0)
            width = min(
                max_width,
                max(34.0, float(intrinsic.width) + 16.0),
            )
            height = max(24.0, float(intrinsic.height) + 8.0)
            label.setFrame_(NSMakeRect(8, 4, width - 16.0, height - 8.0))
            effect.setFrame_(NSMakeRect(0, 0, width, height))

            screen_top = float(screen_frame.origin.y + screen_frame.size.height)
            cocoa_y = screen_top - float(y) - height - 4.0
            panel_x = min(
                max(float(x) - width / 2.0, float(visible_frame.origin.x) + 4.0),
                float(visible_frame.origin.x + visible_frame.size.width)
                - width
                - 4.0,
            )
            cocoa_y = min(
                max(cocoa_y, float(visible_frame.origin.y) + 4.0),
                float(visible_frame.origin.y + visible_frame.size.height)
                - height
                - 4.0,
            )
            panel.setFrame_display_(
                NSMakeRect(panel_x, cocoa_y, width, height),
                True,
            )
            panel.orderFrontRegardless()
        except Exception:
            logger.debug("Could not show native macOS tooltip", exc_info=True)

    @Slot()
    def hideToolTip(self) -> None:
        if sys.platform == "darwin" and self._tooltip_panel is not None:
            self._tooltip_panel.orderOut_(None)

    def _ensure_tooltip_panel(self) -> None:
        if self._tooltip_panel is not None:
            return
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 80, 24),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        panel.setLevel_(NSFloatingWindowLevel)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setHasShadow_(True)
        panel.setIgnoresMouseEvents_(True)

        effect = NSVisualEffectView.alloc().initWithFrame_(panel.contentView().bounds())
        effect.setBlendingMode_(NSVisualEffectBlendingModeWithinWindow)
        effect.setMaterial_(NSVisualEffectMaterialToolTip)
        effect.setState_(NSVisualEffectStateActive)
        effect.setWantsLayer_(True)
        effect.layer().setCornerRadius_(6.0)
        effect.layer().setMasksToBounds_(True)

        label = NSTextField.labelWithString_("")
        label.cell().setWraps_(False)
        effect.addSubview_(label)
        panel.setContentView_(effect)
        self._tooltip_panel = panel
        self._tooltip_label = label
        self._tooltip_effect = effect

    @Slot(result=str)
    def newComboMenuToken(self) -> str:
        self._combo_token += 1
        return f"combo-{self._combo_token}"

    @Slot(str, "QVariantList", int, float, float)
    def showComboMenu(
        self,
        token: str,
        labels: list[Any],
        current_index: int,
        x: float,
        y: float,
    ) -> None:
        """Open a real NSMenu for a QML ComboBox."""
        if sys.platform != "darwin" or not labels:
            return
        try:
            if self._combo_menu_target is None:
                self._combo_menu_target = (
                    _ComboMenuTarget.alloc().initWithOwner_(self)
                )
            menu = NSMenu.alloc().initWithTitle_("")
            menu.setAutoenablesItems_(False)
            items = []
            for index, label in enumerate(labels):
                item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    str(label), "comboItemSelected:", ""
                )
                item.setTarget_(self._combo_menu_target)
                item.setRepresentedObject_(token)
                item.setTag_(index)
                item.setEnabled_(True)
                menu.addItem_(item)
                items.append(item)

            app = NSApplication.sharedApplication()
            ns_window = app.keyWindow() or self._ns_window
            if ns_window is None:
                return
            view = ns_window.contentView()
            window_point = ns_window.mouseLocationOutsideOfEventStream()
            view_point = view.convertPoint_fromView_(window_point, None)
            selected = (
                items[current_index]
                if 0 <= current_index < len(items)
                else None
            )
            menu.popUpMenuPositioningItem_atLocation_inView_(
                selected, view_point, view
            )
        except Exception:
            logger.debug("Could not open native macOS combo menu", exc_info=True)

    def _configure_application_menu(self, delegate: QObject) -> None:
        main_menu = NSApplication.sharedApplication().mainMenu()
        if main_menu is None or main_menu.numberOfItems() == 0:
            return
        app_menu = main_menu.itemAtIndex_(0).submenu()
        if app_menu is None:
            return

        items = list(app_menu.itemArray())

        def represented_object(item: NSMenuItem) -> str:
            value = item.representedObject()
            return "" if value is None else str(value)

        def normalized_title(item: NSMenuItem) -> str:
            return str(item.title()).strip().lower()

        about_item = next(
            (
                item
                for item in items
                if represented_object(item) == "dm.about-menu"
            ),
            None,
        )
        if about_item is None:
            about_item = next(
                (
                    item
                    for item in items
                    if (
                        normalized_title(item).startswith("about ")
                        and normalized_title(item) != "about qt"
                    )
                    or normalized_title(item).startswith("о программе")
                ),
                None,
            )
        if about_item is None:
            about_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "О Dubbing Manager", "openAbout:", ""
            )
            app_menu.insertItem_atIndex_(about_item, 0)
        about_item.setTitle_("О Dubbing Manager")
        about_item.setAction_("openAbout:")
        about_item.setTarget_(delegate)
        about_item.setRepresentedObject_("dm.about-menu")

        settings_titles = {
            "preferences...",
            "preferences…",
            "settings...",
            "settings…",
            "настройки...",
            "настройки…",
            "параметры...",
            "параметры…",
        }
        settings_item = next(
            (
                item
                for item in items
                if represented_object(item) == "dm.settings-menu"
            ),
            None,
        )
        if settings_item is None:
            settings_item = next(
                (
                    item
                    for item in items
                    if normalized_title(item) in settings_titles
                ),
                None,
            )
        if settings_item is None:
            settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Настройки…", "openSettings:", ","
            )
            app_menu.insertItem_atIndex_(
                settings_item, app_menu.indexOfItem_(about_item) + 1
            )
        settings_item.setTitle_("Настройки…")
        settings_item.setAction_("openSettings:")
        settings_item.setTarget_(delegate)
        settings_item.setKeyEquivalent_(",")
        settings_item.setRepresentedObject_("dm.settings-menu")

    def refresh_recent_projects(self) -> None:
        if self._delegate is not None:
            self._delegate.refresh_recent_projects()

    def _validate_toolbar(self) -> None:
        if self._toolbar is not None:
            self._toolbar.validateVisibleItems()
