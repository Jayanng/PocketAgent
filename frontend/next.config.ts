import path from "path";
import type { NextConfig } from "next";

const frontendRoot = __dirname;

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: frontendRoot,
  allowedDevOrigins: ["localhost", "127.0.0.1"],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "picsum.photos",
      },
      {
        protocol: "https",
        hostname: "cdn.simpleicons.org",
      },
    ],
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  experimental: {
    optimizePackageImports: ["lucide-react", "motion", "@phosphor-icons/react"],
  },
  turbopack: {
    resolveAlias: {
      "@react-native-async-storage/async-storage": "./src/lib/stubs/async-storage.ts",
    },
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      "@react-native-async-storage/async-storage": path.join(
        frontendRoot,
        "src/lib/stubs/async-storage.ts",
      ),
    };
    return config;
  },
};

export default nextConfig;