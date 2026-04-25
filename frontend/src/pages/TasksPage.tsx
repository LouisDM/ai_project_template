import { useState, useEffect } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, Radio, DatePicker, Tag, Space,
  Statistic, Row, Col, Popconfirm, Switch, Typography, message,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { listTasks, createTask, updateTask, deleteTask, type Task, type TaskCreate } from '../api/tasks';

const { TextArea } = Input;
const { Title } = Typography;

const priorityColors: Record<string, string> = {
  high: 'red',
  medium: 'orange',
  low: 'green',
};

const priorityLabels: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<string>('all');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [form] = Form.useForm();

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const status = filter === 'all' ? undefined : filter;
      const res = await listTasks(status);
      setTasks(res.data);
    } catch {
      message.error('加载任务失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [filter]);

  const handleSubmit = async (values: any) => {
    const data: TaskCreate = {
      title: values.title,
      description: values.description || '',
      priority: values.priority,
      due_date: values.due_date ? values.due_date.format('YYYY-MM-DD HH:mm:ss') : null,
    };

    try {
      if (editingTask) {
        await updateTask(editingTask.id, { ...data, status: values.status ? 'done' : 'todo' });
        message.success('任务已更新');
      } else {
        await createTask(data);
        message.success('任务已创建');
      }
      setModalVisible(false);
      setEditingTask(null);
      form.resetFields();
      fetchTasks();
    } catch {
      message.error('操作失败');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteTask(id);
      message.success('任务已删除');
      fetchTasks();
    } catch {
      message.error('删除失败');
    }
  };

  const openEdit = (task: Task) => {
    setEditingTask(task);
    form.setFieldsValue({
      title: task.title,
      description: task.description,
      priority: task.priority,
      status: task.status === 'done',
      due_date: task.due_date ? dayjs(task.due_date) : null,
    });
    setModalVisible(true);
  };

  const openCreate = () => {
    setEditingTask(null);
    form.resetFields();
    form.setFieldsValue({ priority: 'medium' });
    setModalVisible(true);
  };

  const total = tasks.length;
  const todoCount = tasks.filter((t) => t.status === 'todo').length;
  const doneCount = tasks.filter((t) => t.status === 'done').length;

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      render: (text: string, record: Task) => (
        <span style={{ textDecoration: record.status === 'done' ? 'line-through' : 'none', color: record.status === 'done' ? '#999' : '#333' }}>
          {text}
        </span>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 80,
      render: (p: string) => <Tag color={priorityColors[p]}>{priorityLabels[p]}</Tag>,
    },
    {
      title: '截止日期',
      dataIndex: 'due_date',
      width: 140,
      render: (d: string | null) => d ? dayjs(d).format('YYYY-MM-DD') : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (s: string) => s === 'done' ? <Tag color="success">已完成</Tag> : <Tag>待办</Tag>,
    },
    {
      title: '操作',
      width: 120,
      render: (_: any, record: Task) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEdit(record)} />
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)}>
            <Button icon={<DeleteOutlined />} size="small" danger />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card><Statistic title="总任务" value={total} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="待完成" value={todoCount} valueStyle={{ color: '#cf1322' }} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="已完成" value={doneCount} valueStyle={{ color: '#3f8600' }} /></Card>
        </Col>
      </Row>

      <Card
        title={<Title level={5} style={{ margin: 0 }}>任务列表</Title>}
        extra={
          <Space>
            <Radio.Group value={filter} onChange={(e) => setFilter(e.target.value)}>
              <Radio.Button value="all">全部</Radio.Button>
              <Radio.Button value="todo">待办</Radio.Button>
              <Radio.Button value="done">已完成</Radio.Button>
            </Radio.Group>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新建任务
            </Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          dataSource={tasks}
          columns={columns}
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editingTask ? '编辑任务' : '新建任务'}
        open={modalVisible}
        onOk={() => form.submit()}
        onCancel={() => { setModalVisible(false); setEditingTask(null); }}
        okText={editingTask ? '更新' : '创建'}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="title" label="标题" rules={[{ required: true, message: '请输入标题' }]}>
            <Input placeholder="任务标题" maxLength={200} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="任务描述（可选）" />
          </Form.Item>
          <Form.Item name="priority" label="优先级" rules={[{ required: true }]}>
            <Radio.Group>
              <Radio.Button value="low">低</Radio.Button>
              <Radio.Button value="medium">中</Radio.Button>
              <Radio.Button value="high">高</Radio.Button>
            </Radio.Group>
          </Form.Item>
          <Form.Item name="due_date" label="截止日期">
            <DatePicker style={{ width: '100%' }} placeholder="选择截止日期（可选）" />
          </Form.Item>
          {editingTask && (
            <Form.Item name="status" label="状态" valuePropName="checked">
              <Switch checkedChildren="已完成" unCheckedChildren="待办" />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
