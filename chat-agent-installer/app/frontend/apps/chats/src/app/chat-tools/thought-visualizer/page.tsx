'use client';

import { Card, Typography, Alert } from 'antd';
import { BulbOutlined } from '@ant-design/icons';
import ContainerWithSidebar from '@/components/containers/ContainerWithSidebar';

const { Title, Text } = Typography;

export default function ThoughtVisualizerPage() {
  // Get the API base URL from environment or default to relative path
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
  const vizUrl = `${apiBaseUrl}/viz`;

  return (
    <ContainerWithSidebar>
      <Card style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Title level={2}>
          <BulbOutlined /> AI Thought Visualizer
        </Title>
        <Text type="secondary">
          Real-time visualization of AI reasoning and decision-making process
        </Text>

        <Alert
          message="Live Visualization"
          description="This shows the AI's thought process in real-time as it analyzes and responds to queries."
          type="info"
          showIcon
          style={{ marginTop: 16, marginBottom: 16 }}
        />

        <div style={{ flex: 1, minHeight: 0, marginTop: 16 }}>
          <iframe
            src={vizUrl}
            style={{
              width: '100%',
              height: '100%',
              border: '1px solid #d9d9d9',
              borderRadius: 8,
            }}
            title="AI Thought Visualization"
          />
        </div>
      </Card>
    </ContainerWithSidebar>
  );
}
