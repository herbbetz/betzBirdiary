<!--keywords[blog,Github,jekyll]-->

- Der Blog in einem Github Repo wird übersetzt durch den static-site-generator Jekyll (einem Ruby Gem)
- Der Blog wird konfiguriert durch `/_config.yml`, `/index.md` und `Permalinks` im Frontmatter der .md Dateien, dann auch durch die Verzeichnisse `/assets` und `/posts` mit `directory names` als Datumskriterium.

- Ich habe den Blog so konzipiert, dass Jekyll Code in den .md des Blogs nur in /index.md vorkommt.

  Damit sind die anderen .md des Blogs auch außerhalb des Blogs darstellbar und sind dafür mit `keywords` versehen.
  
  Image Links in den Blog .md sind normale `HTML relative links`.
  
- Verschieben des Blog in das /station3/blog Unterverzeichnis des Repo `betzBirdiary`:

