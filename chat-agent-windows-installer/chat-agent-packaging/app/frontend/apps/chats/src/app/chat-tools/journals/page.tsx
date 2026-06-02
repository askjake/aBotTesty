'use client';

import { useEffect, useState } from 'react';
import { List, Empty, Typography, Card, Spin } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import { useAppSelector } from '@shared/ui/store';
import ContainerWithSidebar from '@/components/containers/ContainerWithSidebar';

const { Title, Text } = Typography;

interface JournalMetadata {
  filename: string;
  description?: string;
  chat_id?: string;
  created_at?: string;
}

export default function JournalsPage() {
  const activeChat = useAppSelector((store) => store.chats.activeChat);
  const [journals, setJournals] = useState<JournalMetadata[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchJournals = async () => {
    if (!activeChat?.chat_id) return;
    setLoading(true);
    try {
      const res = await fetch(
        `/rest/api/v1/logassist/journals?chat_id=${activeChat.chat_id}`,
      );
      const data = await res.json();
      setJournals(data.items ?? data ?? []);
    } catch (err) {
      console.error('Failed to fetch journals', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJournals();
  }, [activeChat?.chat_id]);

  return (
    <ContainerWithSidebar>
      <Card style={{ height: '100%' }}>
        <Title level={2}>
          <FileTextOutlined /> Journals
        </Title>
        <Text type="secondary">
          {activeChat?.chat_id
            ? `Journal files for current conversation`
            : 'Select a conversation to view journals'}
        </Text>

        <div style={{ marginTop: 24 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 48 }}>
              <Spin size="large" />
            </div>
          ) : !activeChat?.chat_id ? (
            <Empty description="No active conversation" />
          ) : journals.length === 0 ? (
            <Empty description="No journal files available yet." />
          ) : (
            <List
              dataSource={journals}
              renderItem={(item) => {
                const j = item as JournalMetadata;
                return (
                  <List.Item>
                    <List.Item.Meta
                      title={j.filename}
                      description={j.description ?? 'No description'}
                    />
                  </List.Item>
                );
              }}
            />
          )}
        </div>
      </Card>
    </ContainerWithSidebar>
  );
}
