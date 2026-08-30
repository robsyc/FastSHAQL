"""GraphiQL browser IDE HTML (GraphiQL 5.x via esm.sh import map).

Includes the ``@graphiql/plugin-explorer`` checkbox sidebar plugin, rendered
as a GraphiQL plugin (left sidebar) alongside the query editor and Docs pane.
"""

GRAPHIQL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GraphiQL</title>
  <link
    rel="stylesheet"
    href="https://esm.sh/graphiql@5.2.4/dist/style.css"
    integrity="sha384-TFpQQKp325U5sd3PddH4cS0KOB3Gz/aqdEe12Mqkkq3wm2MGcDhRX5WhWf+o8akh"
    crossorigin="anonymous"
  />
  <link
    rel="stylesheet"
    href="https://esm.sh/@graphiql/plugin-explorer@5.1.3/dist/style.css"
    integrity="sha384-vTFGj0krVqwFXLB7kq/VHR0/j2+cCT/B63rge2mULaqnib2OX7DVLUVksTlqvMab"
    crossorigin="anonymous"
  />
  <style>
    body { margin: 0; }
    #graphiql { height: 100dvh; }
    .loading {
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 2rem;
    }
  </style>
  <script type="importmap">
  {
    "imports": {
      "react": "https://esm.sh/react@19.2.7",
      "react/": "https://esm.sh/react@19.2.7/",
      "react-dom": "https://esm.sh/react-dom@19.2.7",
      "react-dom/": "https://esm.sh/react-dom@19.2.7/",
      "graphiql": "https://esm.sh/graphiql@5.2.4?standalone&external=react,react-dom,@graphiql/react,graphql",
      "graphiql/": "https://esm.sh/graphiql@5.2.4/",
      "@graphiql/plugin-explorer": "https://esm.sh/@graphiql/plugin-explorer@5.1.3?standalone&external=react,@graphiql/react,graphql",
      "@graphiql/react": "https://esm.sh/@graphiql/react@0.37.7?standalone&external=react,react-dom,graphql,@graphiql/toolkit,@emotion/is-prop-valid",
      "@graphiql/toolkit": "https://esm.sh/@graphiql/toolkit@0.12.1?standalone&external=graphql",
      "graphql": "https://esm.sh/graphql@16.14.2",
      "@emotion/is-prop-valid": "data:text/javascript,"
    },
    "integrity": {
      "https://esm.sh/react@19.2.7": "sha384-LO2cBox9zBA6AOWqno07582eanOcJxJyu4hwf3rg5CrZQ/XoPtgSAFlL6ezpFK0O",
      "https://esm.sh/react-dom@19.2.7": "sha384-upKKG1ShVOSXNAoNmdKSl8xWJl9L8fZ05Ki1rHXpPijT4hIS/FFh+88dxk72+jre",
      "https://esm.sh/graphiql@5.2.4?standalone&external=react,react-dom,@graphiql/react,graphql": "sha384-n1sWmquV8wXH/vbn5Q8BaQAw8iAFku5zAs2fPBrht0L/OP4/qgZWL/v/WhMLFPBH",
      "https://esm.sh/@graphiql/plugin-explorer@5.1.3?standalone&external=react,@graphiql/react,graphql": "sha384-HKY9iI+ifQ4YM8OnU90+Z8Um79xfL5+xMR1D97SDPdHufGTJAArdx3pLOgsetMDa",
      "https://esm.sh/@graphiql/react@0.37.7?standalone&external=react,react-dom,graphql,@graphiql/toolkit,@emotion/is-prop-valid": "sha384-U8awo9eG6M8scx4fjis/pNfYja4d5EtxOFYcmvDGG8K4Rt/bGB6Km1hxbQXZr9qH",
      "https://esm.sh/@graphiql/toolkit@0.12.1?standalone&external=graphql": "sha384-+cNTwZgIW33q7A4E+ZoCMqzcXdfVIc2VthQvJ0uDpRXERBWYuDKPVMzvdQU8x48o",
      "https://esm.sh/graphql@16.14.2": "sha384-pscTxVTYJfGgTyn8STZjNJN16RVdVsPb1mdoEpaUBrKcONIVebHWTr4BB1QMZLJT"
    }
  }
  </script>
</head>
<body>
  <div id="graphiql"><div class="loading">Loading…</div></div>
  <script type="module">
    import React from 'react';
    import ReactDOM from 'react-dom/client';
    import { GraphiQL } from 'graphiql';
    import { createGraphiQLFetcher } from '@graphiql/toolkit';
    import { explorerPlugin } from '@graphiql/plugin-explorer';
    import 'graphiql/setup-workers/esm.sh';

    const fetcher = createGraphiQLFetcher({ url: window.location.pathname });
    // explorerPlugin() needs no schema/edit wiring: it pulls the schema from
    // GraphiQL's store (useGraphiQL) and writes field clicks back into the
    // operations editor (useOperationsEditorState) automatically.
    const explorer = explorerPlugin();
    const root = ReactDOM.createRoot(document.getElementById('graphiql'));
    root.render(
      React.createElement(GraphiQL, {
        fetcher,
        plugins: [explorer],
        defaultEditorToolsVisibility: true,
      }),
    );
  </script>
</body>
</html>
"""
