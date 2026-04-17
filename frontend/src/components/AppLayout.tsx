import { useState } from 'react';
import { Layout, Menu, Button, Typography } from 'antd';
import { AppstoreOutlined, LogoutOutlined, UserOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Header, Content } = Layout;
const { Title } = Typography;

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [memberName] = useState(() => {
    try {
      const raw = localStorage.getItem('member');
      if (raw) return (JSON.parse(raw) as { name?: string }).name || '';
    } catch {
      /* ignore */
    }
    return '';
  });

  const menuItems = [
    { key: '/', label: 'Items', icon: <AppstoreOutlined /> },
  ];

  const selectedKey = menuItems.find((m) => location.pathname === m.key)?.key || '/';

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('member');
    navigate('/login');
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          background: '#fff',
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          borderBottom: '1px solid #e2e8f0',
        }}
      >
        <Title level={4} style={{ margin: 0, marginRight: 32, color: '#1a56db' }}>
          AI Project Template
        </Title>
        <Menu
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ flex: 1, border: 'none' }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {memberName && (
            <span style={{ color: '#64748b' }}>
              <UserOutlined /> {memberName}
            </span>
          )}
          <Button icon={<LogoutOutlined />} onClick={handleLogout}>
            登出
          </Button>
        </div>
      </Header>
      <Content style={{ padding: 24 }}>{children}</Content>
    </Layout>
  );
}
