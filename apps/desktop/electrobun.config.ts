export default {
  app: {name: "AstraFactory", identifier: "dev.astrafactory.desktop", version: "0.1.0"},
  build: {mainProcess: "bun", bun: {entrypoint: "src/main/desktop.ts"}, copy: {"dist": "views/app"}},
  runtime: {exitOnLastWindowClosed: true}
};
