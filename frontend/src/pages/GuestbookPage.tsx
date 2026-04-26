import { useState, useEffect } from 'react';
import { Form, Input, Button, Typography, Divider, message, Empty } from 'antd';
import type { Guestbook } from '../types';
import { listGuestbooks, createGuestbook } from '../api/guestbook';

const { Title, Text } = Typography;
const { TextArea } = Input;

function formatTime(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export default function GuestbookPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Guestbook[]>([]);
  const [fetching, setFetching] = useState(true);

  const fetchMessages = async () => {
    setFetching(true);
    try {
      const data = await listGuestbooks();
      setMessages(Array.isArray(data) ? data : []);
    } catch {
      message.error('获取留言失败');
      setMessages([]);
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, []);

  const handleSubmit = async (values: { name: string; content: string }) => {
    setLoading(true);
    try {
      await createGuestbook({ name: values.name.trim(), content: values.content.trim() });
      message.success('留言成功');
      form.resetFields();
      await fetchMessages();
    } catch (err: unknown) {
      const resp =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response
          : undefined;
      message.error(resp?.data?.detail || '提交失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px 16px' }}>
      <Title level={3} style={{ color: '#1e293b', marginBottom: 24 }}>
        留言板
      </Title>

      <div style={{ background: '#fff', padding: 24, borderRadius: 8, border: '1px solid #e2e8f0' }}>
        <Form layout="vertical" form={form} onFinish={handleSubmit}>
          <Form.Item
            label="姓名"
            name="name"
            rules={[{ required: true, message: '请输入姓名' }, { max: 50, message: '姓名不能超过50字' }]}
          >
            <Input placeholder="您的姓名" data-testid="guestbook-name" />
          </Form.Item>
          <Form.Item
            label="留言内容"
            name="content"
            rules={[{ required: true, message: '请输入留言内容' }, { max: 2000, message: '内容不能超过2000字' }]}
          >
            <TextArea placeholder="写下您的留言..." rows={4} data-testid="guestbook-content" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} data-testid="guestbook-submit">
              提交
            </Button>
          </Form.Item>
        </Form>
      </div>

      <Divider />

      <Title level={4} style={{ color: '#1e293b', marginBottom: 16 }}>
        留言列表
      </Title>

      {fetching ? (
        <Text type="secondary">加载中...</Text>
      ) : messages.length === 0 ? (
        <Empty description="暂无留言，快来抢沙发" />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                background: '#fff',
                padding: 16,
                borderRadius: 8,
                border: '1px solid #e2e8f0',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <Text strong style={{ color: '#1a56db' }}>{msg.name}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>{formatTime(msg.created_at)}</Text>
              </div>
              <Text style={{ color: '#334155', whiteSpace: 'pre-wrap' }}>{msg.content}</Text>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
