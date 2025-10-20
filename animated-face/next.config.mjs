/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export', // Enable static export for Capacitor
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  trailingSlash: true, // Required for static export
}

export default nextConfig
