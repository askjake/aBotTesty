import { Typography } from 'antd';
import { StyledFAQVaultBlock } from '@/components/organisms/VaultMode/FAQVaultBlock/FAQVaultBlock.styled';
const { Paragraph, Text } = Typography;

const FAQVaultBlock = () => {
  return (
    <StyledFAQVaultBlock
      size='large'
      defaultActiveKey={['1', '2']}
      items={[
        {
          key: '1',
          label: 'What is Vault Mode?',
          children: (
            <>
              <Paragraph>
                Vault mode is a togglable mode that enables extra encryption on
                your chat conversations and documents with your own passphrase.
              </Paragraph>
              <Paragraph>
                <Text strong>
                  However, if you lose your passphrase, all your data in vault
                  will be lost and cannot be recovered.
                </Text>
              </Paragraph>
              <Paragraph>
                <ul>
                  <li>
                    Outside of vault mode, all data is still encrypted at rest
                    with app-managed key and encrypted in transit with HTTPS to
                    protect against data leak.
                  </li>
                </ul>
              </Paragraph>
            </>
          ),
        },
        {
          key: '2',
          label: 'Passphrase requirements',
          children: (
            <>
              <Paragraph>
                <ul>
                  <li>Between 8 and 32 characters long.</li>
                  <li>
                    Contains only alphabets, numbers, and special characters
                    from: {"#$%&'()*+,-./:;<=>?@[]^_`{|}~"}
                  </li>
                  <li>Contains at least 1 lower case alphabet.</li>
                  <li>Contains at least 1 upper case alphabet.</li>
                  <li>Contains at least 1 number.</li>
                  <li>
                    Contains at least 1 special character in:{' '}
                    {`#$%&'()*+,-./:;<=>?@[]^_\`{|}~`}
                  </li>
                </ul>
              </Paragraph>
            </>
          ),
        },
      ]}
    />
  );
};

export default FAQVaultBlock;
