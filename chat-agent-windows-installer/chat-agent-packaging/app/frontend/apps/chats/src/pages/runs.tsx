// apps/chats/src/pages/runs.tsx
import React, { useEffect, useState } from 'react';
import type { NextPage } from 'next';
import { Typography, List, Tag, Empty, Spin, Button } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import ContainerWithSidebar from '@/components/containers/ContainerWithSidebar';

const { Title, Text } = Typography;

interface AgentRun {
  id: string;
  command?: string;
  repo_url?: string;
  chat_id?: string;
  status: 'running' | 'succeeded' | 'failed' | 'pending';
  started_at?: string;
  completed_at?: string;
  error?: string;
  artifacts?: string[];
}

const statusIcons: Record<AgentRun['status'], React.ReactElement> = {
  running: <SyncOutlined spin style={{ color: '#1890ff' }} />,
  pending: <SyncOutlined style={{ color: '#8c8c8c' }} />,
  succeeded: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  failed: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
};

const statusColors: Record<AgentRun['status'], 'processing' | 'default' | 'success' | 'error'> =
  {
    running: 'processing',
    pending: 'default',
    succeeded: 'success',
    failed: 'error',
  };

const RunsPage: NextPage = () => {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    const load = async () => {
      setLoading(true);
      try {
        const res = await fetch('/rest/api/v1/agent-mode/runs', {
          signal: controller.signal,
        });
        if (res.ok) {
          const data = await res.json();
          setRuns(data.items ?? data);
        }
      } catch (err) {
        console.warn('Failed to load runs', err);
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
        <Title level={3}>Automation Runs</Title>
        <Text type="secondary">
          View agent mode execution history, including code runs, git operations, and
          generated artifacts.
        </Text>

        <div style={{ marginTop: 24 }}>
          {loading ? (
            <Spin />
          ) : runs.length === 0 ? (
            <Empty description="No automation runs yet. Use agent mode in a chat to create one." />
          ) : (
            <List
              itemLayout="horizontal"
              dataSource={runs}
              renderItem={(run) => (
                <List.Item
                  actions={[
                    run.chat_id ? (
                      <Button
                        key="open-chat"
                        type="link"
                        onClick={() => (window.location.href = `/?chat_id=${run.chat_id}`)}
                      >
                        Open chat
                      </Button>
                    ) : null,
                    <Button
                      key="view-details"
                      type="link"
                      onClick={() =>
                        window.dispatchEvent(
                          new CustomEvent('open-run-details', {
                            detail: { id: run.id },
                          }),
                        )
                      }
                    >
                      View details
                    </Button>,
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    avatar={statusIcons[run.status]}
                    title={
                      <>
                        {run.command || run.id}
                        <Tag
                          color={statusColors[run.status]}
                          style={{ marginLeft: 8, textTransform: 'capitalize' }}
                        >
                          {run.status}
                        </Tag>
                      </>
                    }
                    description={
                      <>
                        <Text type="secondary">
                          {run.started_at
                            ? new Date(run.started_at).toLocaleString()
                            : ''}
                        </Text>
                        {run.completed_at && (
                          <>
                            {' → '}
                            <Text type="secondary">
                              {new Date(run.completed_at).toLocaleString()}
                            </Text>
                          </>
                        )}
                        {run.repo_url && (
                          <>
                            <br />
                            <Text type="secondary">{run.repo_url}</Text>
                          </>
                        )}
                        {run.error && (
                          <>
                            <br />
                            <Text type="danger">{run.error}</Text>
                          </>
                        )}
                        {run.artifacts?.length ? (
                          <>
                            <br />
                            <Text type="secondary">
                              {run.artifacts.length} artifact(s)
                            </Text>
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

export default RunsPage;

