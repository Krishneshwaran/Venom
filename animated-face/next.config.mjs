/** @type {import('next').NextConfig} */
const nextConfig = {
  // Removed output: 'export' - we need server-side API routes for MongoDB
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
