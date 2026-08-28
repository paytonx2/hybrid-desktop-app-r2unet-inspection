export const metadata = {
  title: 'R2U-NET Inspection Dashboard',
  description: 'Real-time defect inspection monitoring',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: '#f4f5f9', fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif' }}>
        {children}
      </body>
    </html>
  );
}
