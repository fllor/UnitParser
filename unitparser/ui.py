#!/usr/bin/env python3

import sys
import math
import curses
import curses.textpad

import unitparser

class WindowTooSmallExeception(Exception):
    pass

class UI:
    def __init__(self, scr):
        self.scr = scr
        self.scr.keypad(True)
        curses.cbreak()
        self.history = []
        self.init_screen()
        self.textpad = None

    def init_screen(self):
        curses.update_lines_cols()
        self.y = curses.LINES
        self.x = curses.COLS
        if self.y < 4:
            raise WindowTooSmallExeception()
        self.input_height = 1
        if self.y > 40:
            self.input_height = 3
        elif self.y > 20:
            self.input_height = 2
        self.win_history = curses.newwin(self.y - self.input_height - 3, self.x - 2, 1, 1)
        self.win_edit = curses.newwin(self.input_height, self.x - 2, self.y - self.input_height - 1, 1)

    def draw_background(self):
        self.scr.clear()
        self.scr.border()
        line_height = self.y - self.input_height - 2
        self.scr.addch(line_height, 0, curses.ACS_LTEE)
        self.scr.addch(line_height, self.x - 1, curses.ACS_RTEE)
        self.scr.hline(line_height, 1, curses.ACS_HLINE, self.x - 2)
        self.scr.refresh()

    def split_text_for_history(self, text):
        lines = []
        w = self.x - 2
        for i in range(math.ceil(len(text)/w)):
            lines.append(text[i*w : (i+1)*w])
        return lines
    
    def draw_history(self):
        self.win_history.clear()
        lines = []
        for i, entry in enumerate(self.history):
            mark = f"[{i+1}] "
            indent = " "*len(mark)
            lines.extend(self.split_text_for_history(mark + entry[0]))
            for line in entry[1].split("\n"):
                lines.extend(self.split_text_for_history(indent + line))
        for i, line in enumerate(lines[-(self.y-self.input_height-3):]):
            self.win_history.addstr(i, 0, line)
        self.win_history.refresh()

    def draw_edit(self):
        self.win_edit.refresh()
        if self.textpad is None:
            self.textpad = curses.textpad.Textbox(self.win_edit, insert_mode=True)
        else:
            self.textpad.win = self.win_edit
        self.win_edit.refresh()

    def draw_screen(self):
        self.draw_background()
        self.draw_history()
        self.draw_edit()

    def validate(self, c):
        if c == 10:             # return
            return 7
        if c in (127, 263):     # backspace
            return 263
        if c == curses.KEY_DC:  # delete
            return 4
        if c == 4:              # Ctrl + D
            raise KeyboardInterrupt()
        if ord("a") <= c <= ord("z") or \
                ord("A") <= c <= ord("Z") or \
                ord("0") <= c <= ord("9") or \
                chr(c) in ".,+-*/()^ " or \
                c == curses.KEY_LEFT:
            return c
        if c == curses.KEY_UP:
            if self.hist_entry > 0:
                self.hist_entry -= 1
                self.win_edit.clear()
                self.win_edit.addstr(0, 0, self.history[self.hist_entry][0])
                self.win_edit.refresh()
            return 0
        if c == curses.KEY_DOWN:
            if self.hist_entry < len(self.history):
                self.hist_entry += 1
                self.win_edit.clear()
                if self.hist_entry < len(self.history):
                    self.win_edit.addstr(0, 0, self.history[self.hist_entry][0])
                self.win_edit.refresh()
            return 0
        if c in (curses.KEY_RIGHT, curses.KEY_END):
            y, x = self.win_edit.getyx()
            last = self.textpad._end_of_line(y)
            if c == curses.KEY_RIGHT:
                self.win_edit.move(y, x + int(x < last))
            else:
                self.win_edit.move(y, last)
            return 0
        if c == curses.KEY_HOME:
            return curses.ascii.SOH
        if c == curses.KEY_RESIZE:  # window resized
            input = self.textpad.gather().strip()
            self.init_screen()
            self.draw_screen()
            self.win_edit.addstr(0, 0, input)
            self.win_edit.move(0, len(input))
            return 0
        
        return 0 # unsupported button

    def run(self):
        self.hist_entry = len(self.history)
        self.win_edit.clear()
        validator = lambda c: self.validate(c)
        input = self.textpad.edit(validator).strip()
        if len(input) == 0:
            input = "help"

        self.history.append((input, self.parse(input)))
        self.draw_history()

    def parse(self, input):
        try:
            if " in " in input:
                split = input.split(" in ")
                if len(split) > 2:
                    return "Too many \"in\" keywords"
                val = unitparser.parse(split[0])
                unit = unitparser.parse(split[1])
                return str(val / unit)
            if input == "help":
                cfg = unitparser._get_parser().cfg
                def to_str(units):
                    return ", ".join([f"{x.name} ({x.symbol})" for x in units])
                msg = "Base units: " + to_str(cfg.base_units)
                msg += "\nDerived units: " + to_str(cfg.derived_units)
                msg += "\nConstants: " + to_str(cfg.constants)
                msg += "\nFunctions: " + ", ".join(cfg.functions.keys())
                return msg
            return str(unitparser.parse(input))
        except Exception as e:
            return str(e)


def main():
    unitparser.init()
    def main(scr):
        ui = UI(scr)
        ui.draw_screen()
        while True:
            ui.run()

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except WindowTooSmallExeception:
        print("Error: Window too small", file=sys.stderr)


if __name__ == "__main__":
	main()
