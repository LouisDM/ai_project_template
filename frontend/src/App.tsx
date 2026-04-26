import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import theme from './theme';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import ItemsPage from './pages/ItemsPage';
import TasksPage from './pages/TasksPage';
import GuestbookPage from './pages/GuestbookPage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminGuestbookPage from './pages/AdminGuestbookPage';

function ProtectedPage({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <AppLayout>{children}</AppLayout>
    </ProtectedRoute>
  );
}

function AdminProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('admin_token');
  if (!token) {
    return <Navigate to="/admin/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={theme}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedPage>
                <ItemsPage />
              </ProtectedPage>
            }
          />
          <Route
            path="/tasks"
            element={
              <ProtectedPage>
                <TasksPage />
              </ProtectedPage>
            }
          />
          <Route path="/guestbook" element={<GuestbookPage />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route
            path="/admin/guestbook"
            element={
              <AdminProtectedRoute>
                <AdminGuestbookPage />
              </AdminProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}
