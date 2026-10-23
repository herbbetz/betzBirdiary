<!--keywords[VSCode]-->

VS Code puts both plain text and rich HTML with syntax highlighting on the clipboard, and Notepad++ only puts plain text. A web input that reads the HTML version can turn it into a fenced block, and the `python` label I received fits that.

Two ways to stop it:

- **VS Code setting:** set `"editor.copyWithSyntaxHighlighting": false` in your settings. VS Code then copies plain text only, which should behave like Notepad++.
- **Paste shortcut:** paste with Ctrl+Shift+V, which pastes plain text in most browsers and skips the HTML.