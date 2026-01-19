export default function HomePage() {
  // Dashboard is the home.
  if (typeof window !== "undefined") window.location.href = "/dashboard";
  return null;
}

