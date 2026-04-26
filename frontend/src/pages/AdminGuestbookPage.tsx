import { useState, useEffect } from 'react';
import { Layout, Button, Typography, Table, Popconfirm, message, Empty } from 'antd';
import { LogoutOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { Guestbook } from '../types';
import { adminListGuestbooks, adminDeleteGuestbook } from '../api/admin';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

function formatTime(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export default function AdminGuestbookPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Guestbook[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchMessages = async () => {
    setLoading(true);
    try {
      const data = await adminListGuestbooks();
      setMessages(Array.isArray(data) ? data : []);
    } catch {
      message.error('获取留言失败');
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, []);

  const handleDelete = async (id: number) => {
    try {
      await adminDeleteGuestbook(id);
      message.success('删除成功');
      setMessages((prev) => prev.filter((m) => m.id !== id));
    } catch {
      message.error('删除失败');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    navigate('/admin/login');
  };

  const columns = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 120,
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      render: (text: string) => <Text style={{ whiteSpace: 'pre-wrap' }}>{text}</Text>,
    },
    {
      title: '提交时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (iso: string) => formatTime(iso),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: Guestbook) => (
        <Popconfirm
          title="确认删除"
          description="删除后该留言将不再显示在公开页面"
          onConfirm={() => handleDelete(record.id)}
          okText="确定"
          cancelText="取消"
        >
          <Button danger size="small">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          background: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          borderBottom: '1px solid #e2e8f0',
        }}
      >
        <Title level={4} style={{ margin: 0, color: '#1a56db' }}>
          留言板管理后台
        </Title>
        <Button icon={<LogoutOutlined />} onClick={handleLogout}>
          退出登录
        </Button>
      </Header>
      <Content style={{ padding: 24 }}>
        {messages.length === 0 && !loading ? (
          <Empty description="暂无留言" />
        ) : (
          <Table
            dataSource={messages}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={false}
          />
        )}
      </Content>
    </Layout>
  );
}
