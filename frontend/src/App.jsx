import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import Sidebar from './components/layout/Sidebar';
import Login from './pages/Login';
import Chat from './pages/Chat';
import Documents from './pages/Documents';
import Analytics from './pages/Analytics';
import Admin from './pages/Admin';

function ProtectedLayout({
  children,
  requiredRole,
  isCollapsed,
  toggleSidebar,
  isMobileOpen,
  toggleMobileSidebar,
  closeMobileSidebar,
  onNewChat,
  activeSessionId,
  onSelectSession
}) {
  const { user, accessToken } = useAuthStore();
  if (!accessToken) return <Navigate to="/login" replace />;
  if (requiredRole && !requiredRole.includes(user?.role)) return <Navigate to="/chat" replace />;
  return (
    <div className={`app-shell ${isCollapsed ? 'sidebar-collapsed' : ''} ${isMobileOpen ? 'mobile-open' : ''}`}>
      {isMobileOpen && <div className="sidebar-backdrop" onClick={closeMobileSidebar} />}
      <Sidebar
        isCollapsed={isCollapsed}
        toggleSidebar={toggleSidebar}
        closeMobileSidebar={closeMobileSidebar}
        onNewChat={onNewChat}
        activeSessionId={activeSessionId}
        onSelectSession={onSelectSession}
      />
      <div className="main-content-gpt">
        {React.cloneElement(children, {
          isCollapsed,
          toggleSidebar,
          isMobileOpen,
          toggleMobileSidebar,
          closeMobileSidebar,
          activeSessionId,
          onSelectSession,
          onNewChat
        })}
      </div>
    </div>
  );
}

export default function App() {
  const { accessToken } = useAuthStore();
  const [isCollapsed, setIsCollapsed] = React.useState(false);
  const [isMobileOpen, setIsMobileOpen] = React.useState(false);
  const [activeSessionId, setActiveSessionId] = React.useState(null);

  const toggleSidebar = () => setIsCollapsed(prev => !prev);
  const toggleMobileSidebar = () => setIsMobileOpen(prev => !prev);
  const closeMobileSidebar = () => setIsMobileOpen(false);
  const handleNewChat = () => { setActiveSessionId(null); closeMobileSidebar(); };
  const handleSelectSession = (sid) => { setActiveSessionId(sid); closeMobileSidebar(); };

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={accessToken ? <Navigate to="/chat" replace /> : <Login />} />
        <Route path="/chat" element={
          <ProtectedLayout
            isCollapsed={isCollapsed}
            toggleSidebar={toggleSidebar}
            isMobileOpen={isMobileOpen}
            toggleMobileSidebar={toggleMobileSidebar}
            closeMobileSidebar={closeMobileSidebar}
            onNewChat={handleNewChat}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
          >
            <Chat />
          </ProtectedLayout>
        } />
        <Route path="/documents" element={
          <ProtectedLayout
            isCollapsed={isCollapsed}
            toggleSidebar={toggleSidebar}
            isMobileOpen={isMobileOpen}
            toggleMobileSidebar={toggleMobileSidebar}
            closeMobileSidebar={closeMobileSidebar}
            onNewChat={handleNewChat}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
          >
            <Documents />
          </ProtectedLayout>
        } />
        <Route path="/analytics" element={
          <ProtectedLayout
            requiredRole={['manager', 'admin']}
            isCollapsed={isCollapsed}
            toggleSidebar={toggleSidebar}
            isMobileOpen={isMobileOpen}
            toggleMobileSidebar={toggleMobileSidebar}
            closeMobileSidebar={closeMobileSidebar}
            onNewChat={handleNewChat}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
          >
            <Analytics />
          </ProtectedLayout>
        } />
        <Route path="/admin" element={
          <ProtectedLayout
            requiredRole={['admin']}
            isCollapsed={isCollapsed}
            toggleSidebar={toggleSidebar}
            isMobileOpen={isMobileOpen}
            toggleMobileSidebar={toggleMobileSidebar}
            closeMobileSidebar={closeMobileSidebar}
            onNewChat={handleNewChat}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
          >
            <Admin />
          </ProtectedLayout>
        } />
        <Route path="*" element={<Navigate to={accessToken ? '/chat' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  );
}
