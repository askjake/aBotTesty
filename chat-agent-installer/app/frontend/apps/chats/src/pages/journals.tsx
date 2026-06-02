// apps/chats/src/pages/journals.tsx
import React, { useEffect, useState } from 'react';
import type { NextPage } from 'next';
import { Typography, List, Tag, Empty, Spin, Button } from 'antd';
import ContainerWithSidebar from '@/components/containers/ContainerWithSidebar';

const { Title, Text } = Typography;

interface Journal {
  id: string;
  name: string;
  chat_id?: string;
  created_at: string;
  last_modified_at?: string;
  updated_at?: string;
  tags?: string[];
}

const JournalsPage: NextPage = () => {
  const [journals, setJournals] = useState<Journal[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    const load = async () => {
      setLoading(true);
      try {
        const res = await fetch('/rest/api/v1/logassist/journals', {
          signal: controller.signal,
        });
        if (res.ok) {
          const data = await res.json();
          setJournals(data.items ?? data);
        }
      } catch (err) {
        console.warn('Failed to load journals', err);
      } finally {
        setLoading(false);
      }
    };

    load();
    return () => controller.abort();
  }, []);

  return (
    <ContainerWithSidebar>
      <div style={{ padding: 24 }}>
        <Title level={3}>Journals</Title>
        <Text type="secondary">
          Journals are structured workspaces created by Log Assist when it analyzes logs
          and runs workflows.
        </Text>

        <div style={{ marginTop: 24 }}>
          {loading ? (
            <Spin />
          ) : journals.length === 0 ? (
            <Empty description="No journals yet. Analyze some logs from a chat to create one." />
          ) : (
            <List
              itemLayout="horizontal"
              dataSource={journals}
              renderItem={(j) => (
                <List.Item
                  actions={[
                    j.chat_id ? (
                      <Button
                        key="open-chat"
                        type="link"
                        onClick={() => (window.location.href = `/?chat_id=${j.chat_id}`)}
                      >
                        Open chat
                      </Button>
                    ) : null,
                    <Button
                      key="open-journal"
                      type="link"
                      onClick={() =>
                        window.dispatchEvent(
                          new CustomEvent('open-journal', { detail: { id: j.id } }),
                        )
                      }
                    >
                      Open journal
                    </Button>,
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    title={j.name || j.id}
                    description={
                      <>
                        <Text type="secondary">
                          {new Date(
                            j.updated_at || j.last_modified_at || j.created_at,
                          ).toLocaleString()}
                        </Text>
                        {j.tags?.length ? (
                          <>
                            {' · '}
                            {j.tags.map((t) => (
                              <Tag key={t}>{t}</Tag>
                            ))}
                          </>
                        ) : null}
                      </>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </div>
      </div>
    </ContainerWithSidebar>
  );
};

export default JournalsPage;

