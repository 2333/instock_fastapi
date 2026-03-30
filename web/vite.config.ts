import { existsSync, readFileSync } from "fs";
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

function readVersionFile() {
  const candidates = [
    resolve(__dirname, "..", "VERSION"),
    resolve(__dirname, "VERSION"),
  ];

  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return readFileSync(candidate, "utf-8").trim();
    }
  }

  return null;
}

function readPackageVersion() {
  const packageJsonPath = resolve(__dirname, "package.json");
  const packageJson = JSON.parse(readFileSync(packageJsonPath, "utf-8")) as {
    version?: string;
  };

  return packageJson.version || "dev";
}

const fileVersion = readVersionFile();
const packageVersion = readPackageVersion();

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, "");
  const appVersion =
    env.VITE_APP_VERSION ||
    process.env.APP_VERSION ||
    fileVersion ||
    packageVersion;
  const appGitSha = env.VITE_APP_GIT_SHA || process.env.APP_GIT_SHA || "local";

  return {
    plugins: [vue()],
    define: {
      __APP_VERSION__: JSON.stringify(appVersion),
      __APP_GIT_SHA__: JSON.stringify(appGitSha),
    },
    resolve: {
      alias: {
        "@": resolve(__dirname, "src"),
      },
    },
    server: {
      port: 3000,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: `@import "@/styles/variables.scss";`,
        },
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes("node_modules")) return;

            if (id.includes("echarts") || id.includes("zrender") || id.includes("vue-echarts")) {
              return "charts-vendor";
            }

            if (id.includes("vue-router")) {
              return "router-vendor";
            }

            if (id.includes("pinia") || id.includes("@vueuse")) {
              return "state-vendor";
            }

            if (id.includes("node_modules/vue")) {
              return "vue-vendor";
            }

            return "vendor";
          },
        },
      },
    },
  };
});
