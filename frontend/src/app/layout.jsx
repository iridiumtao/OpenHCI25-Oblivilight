import "../styles/globals.css";

export const metadata = {
  title: "Oblivilight Projector",
  description: "The light projector for Oblivilight.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
} 