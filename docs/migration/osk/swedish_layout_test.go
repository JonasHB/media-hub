package main

import "testing"

func TestSwedishLayoutAndSelectClose(t *testing.T) {
	expected := map[int][2]string{KEY_LEFTBRACE: {"å", "Å"}, KEY_SEMICOLON: {"ö", "Ö"}, KEY_APOSTROPHE: {"ä", "Ä"}, KEY_102ND: {"<", ">"}}
	for _, row := range swedishLayout() {
		for _, k := range row {
			if want, ok := expected[k.Code]; ok {
				if [2]string{k.Label, k.ShiftLabel} != want {
					t.Errorf("wrong Swedish key: %+v", k)
				}
				delete(expected, k.Code)
			}
		}
	}
	if len(expected) != 0 {
		t.Fatalf("missing keys: %v", expected)
	}
	cfg := DefaultConfig().Gamepad
	cfg.Buttons.Close = "select"
	if got := BuildActionMap(cfg).BtnPress[0x13a]; got != ActionSelectToggle {
		t.Fatalf("Select action: %v", got)
	}
}

func TestGuideCanBeForwardedWhileSelectIsConfigured(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Gamepad.Buttons.Close = "select"
	gp := NewGamepadReader(cfg)
	gp.initButtonMap()
	if got := gp.handleButton(0x13c, 1).Type; got != ActionGuideReturn {
		t.Fatalf("Guide action: %v", got)
	}
	if got := gp.handleButton(0x13c, 0).Type; got != ActionNone {
		t.Fatalf("Guide release: %v", got)
	}
}
