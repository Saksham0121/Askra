import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import Sidebar from './components/layout/Sidebar';
import Login from './pages/Login';
import Chat from './pages/Chat';
import Documents from './pages/Documents';
import Analytics from './pages/Analytics';
import Admin from './pages/Admin';

function ProtectedLayout({ children, requiredRole }) {
  const { user, accessToken } = useAuthStore();
  if (!accessToken) return <Navigate to="/login" replace />;
  if (requiredRole && !requiredRole.includes(user?.role)) return <Navigate to="/chat" replace />;
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-content">
        {children}
      </div>
    </div>
  );
}

export default function App() {
  const { accessToken } = useAuthStore();
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={accessToken ? <Navigate to="/chat" replace /> : <Login />} />
        <Route path="/chat" element={<ProtectedLayout><Chat /></ProtectedLayout>} />
        <Route path="/documents" element={<ProtectedLayout><Documents /></ProtectedLayout>} />
        <Route path="/analytics" element={
          <ProtectedLayout requiredRole={['manager', 'admin']}><Analytics /></ProtectedLayout>
        } />
        <Route path="/admin" element={
          <ProtectedLayout requiredRole={['admin']}><Admin /></ProtectedLayout>
        } />
        <Route path="*" element={<Navigate to={accessToken ? '/chat' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  );
}
